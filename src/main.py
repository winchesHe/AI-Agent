from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from dotenv import load_dotenv

load_dotenv()

from core.runtime.config import (  # noqa: E402
    ConfigError,
    ConfigurationProfile,
    find_config_path,
    load_and_validate_profile,
)

# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------
EXIT_OK = 0
EXIT_CLI_USAGE = 2
EXIT_CONFIG = 3
EXIT_EXTERNAL_DEP = 4
EXIT_INTERNAL = 5
EXIT_PLUGIN_LOAD = 6


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def _overlay_cli_plugin_paths(
    profile: ConfigurationProfile,
    args: argparse.Namespace,
) -> ConfigurationProfile:
    """Append ``--plugin-path`` entries to ``plugins.search_paths``."""
    extra = getattr(args, "plugin_path", None) or []
    if not extra:
        return profile
    merged = list(profile.plugins.search_paths)
    for p in extra:
        if p and p not in merged:
            merged.append(p)
    return profile.model_copy(
        update={
            "plugins": profile.plugins.model_copy(update={"search_paths": merged}),
        },
    )


def _close_mcp_bridge(bridge: object | None) -> None:
    if bridge is None:
        return
    try:
        asyncio.run(bridge.close_all())  # type: ignore[attr-defined]
    except Exception:
        logging.getLogger(__name__).debug("MCP close_all failed", exc_info=True)


def _build_runtime(
    args: argparse.Namespace,
    *,
    connect_mcp: bool = True,
):
    """Load config, register built-in + plugin (+ optional MCP) tools.

    Returns
    -------
    profile, llm, registry, mcp_bridge
        *mcp_bridge* is non-``None`` when MCP servers connected; caller must
        :meth:`close_all` when the session ends (see :func:`_close_mcp_bridge`).
    """
    from core.llm.llm_client import HelloAgentsLLM
    from core.hello_agents.tool_registry import ToolRegistry
    from core.hello_agents.tools.search_tool import SearchTool
    from core.runtime.logging_config import setup_logging
    from core.runtime.mcp_bridge import connect_mcp_tools_sync
    from core.runtime.plugin_host import PluginHost

    log = logging.getLogger(__name__)

    try:
        path = find_config_path(args.config)
        profile = load_and_validate_profile(path)
        profile = _overlay_cli_plugin_paths(profile, args)
    except ConfigError:
        raise
    except Exception as exc:
        raise ConfigError(f"Failed to load config: {exc}", field=None) from exc

    if profile.logging:
        setup_logging(
            level=profile.logging.level,
            log_path=profile.logging.path,
            max_bytes=profile.logging.max_bytes,
            backup_count=profile.logging.backup_count,
        )
    else:
        setup_logging()

    llm = HelloAgentsLLM()
    registry = ToolRegistry()
    try:
        registry.register_tool(SearchTool())
    except Exception:
        pass  # search tool may not be available

    host = PluginHost(
        profile.plugins,
        profile.security,
        config_path=path,
        workspace=profile.workspace,
    )
    host.discover()
    host.load_tools(registry)

    mcp_bridge = None
    if connect_mcp and profile.mcp and profile.mcp.servers:
        mcp_bridge = connect_mcp_tools_sync(profile.mcp, registry)
        if mcp_bridge is None:
            log.debug("MCP tools not registered (skipped or failed).")

    return profile, llm, registry, mcp_bridge


def cmd_task(args: argparse.Namespace) -> int:
    profile, llm, registry, mcp_bridge = _build_runtime(args)
    try:
        return _cmd_task_body(args, profile, llm, registry)
    finally:
        _close_mcp_bridge(mcp_bridge)


def _cmd_task_body(
    args: argparse.Namespace,
    profile,
    llm,
    registry,
) -> int:
    from core.runtime.loop_driver import LoopDriver

    if args.inbound_channel and args.inbound_sender:
        from core.runtime.inbound import InboundSource, InboundGate, PairingStore, AccessDeniedError
        source = InboundSource(channel=args.inbound_channel, sender_id=args.inbound_sender)
        store = PairingStore(profile.security.pairing_store_path)
        gate = InboundGate(profile.security, store)
        for pid in profile.security.sensitive_plugin_ids:
            try:
                gate.enforce(source, pid)
            except AccessDeniedError as exc:
                print(f"[task] Access denied: {exc}")
                return EXIT_CONFIG

    driver = LoopDriver(
        llm=llm,
        tool_registry=registry,
        loop_config=profile.loop,
    )
    result = driver.run(args.message, no_tools=args.no_tools)

    print(f"\n{result.answer}")

    if args.trace:
        if args.trace == "json":
            output = result.trace.to_json()
        else:
            output = result.trace.to_human_readable()
        if args.trace_file:
            with open(args.trace_file, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"[trace] Written to {args.trace_file}")
        else:
            print(output)

    return EXIT_OK if result.success else EXIT_EXTERNAL_DEP


def cmd_chat(args: argparse.Namespace) -> int:
    from core.runtime.session import run_chat_loop

    profile, llm, registry, mcp_bridge = _build_runtime(args)
    try:
        run_chat_loop(
            llm=llm,
            tool_registry=registry,
            loop_config=profile.loop,
            trace_format=args.trace,
        )
    finally:
        _close_mcp_bridge(mcp_bridge)
    return EXIT_OK


def cmd_daemon(args: argparse.Namespace) -> int:
    from core.runtime.daemon import run_daemon

    profile, _, _, _ = _build_runtime(args, connect_mcp=False)
    try:
        asyncio.run(run_daemon(profile))
    except KeyboardInterrupt:
        pass
    return EXIT_OK


def cmd_doctor(args: argparse.Namespace) -> int:
    from core.runtime.doctor import run_doctor

    try:
        path = find_config_path(args.config)
        profile = load_and_validate_profile(path)
    except ConfigError as exc:
        print(f"[doctor] Config error: {exc}")
        return EXIT_CONFIG

    report = run_doctor(profile, probe_mcp=args.probe_mcp, config_path=path)
    print(report.to_table())
    return EXIT_OK if report.overall_ok else EXIT_CONFIG


def cmd_health(args: argparse.Namespace) -> int:
    from core.runtime.health import build_health_snapshot

    path = find_config_path(args.config)
    profile, _, _, _ = _build_runtime(args, connect_mcp=False)
    snapshot = build_health_snapshot(profile, config_path=path)
    print(snapshot.to_json())
    return EXIT_OK


def cmd_telegram_run(args: argparse.Namespace) -> int:
    profile, llm, registry, mcp_bridge = _build_runtime(args)
    try:
        from core.runtime.telegram_runner import run_telegram_polling

        run_telegram_polling(profile, llm, registry)
        return EXIT_OK
    except ConfigError as exc:
        logging.getLogger(__name__).error("[telegram] %s", exc)
        print(f"[telegram] {exc}")
        return EXIT_CONFIG
    finally:
        _close_mcp_bridge(mcp_bridge)


def cmd_pair_add(args: argparse.Namespace) -> int:
    from core.runtime.config import find_config_path, load_profile_with_env_override
    from core.runtime.inbound import InboundSource, PairingStore

    path = find_config_path(args.config)
    profile = load_profile_with_env_override(path)
    psp = profile.security.pairing_store_path
    if not psp:
        print("[pair] 未配置 security.pairing_store_path，无法持久化配对")
        return EXIT_CONFIG
    store = PairingStore(psp)
    src = InboundSource(channel=args.channel, sender_id=str(args.sender_id))
    store.add_pairing(src, trust_level=args.trust)
    print(f"[pair] 已配对 {src.channel}:{src.sender_id} (trust={args.trust})")
    return EXIT_OK


def cmd_pair_remove(args: argparse.Namespace) -> int:
    from core.runtime.config import find_config_path, load_profile_with_env_override
    from core.runtime.inbound import InboundSource, PairingStore

    path = find_config_path(args.config)
    profile = load_profile_with_env_override(path)
    psp = profile.security.pairing_store_path
    if not psp:
        print("[pair] 未配置 security.pairing_store_path")
        return EXIT_CONFIG
    store = PairingStore(psp)
    src = InboundSource(channel=args.channel, sender_id=str(args.sender_id))
    store.remove_pairing(src)
    print(f"[pair] 已移除 {src.channel}:{src.sender_id}")
    return EXIT_OK


def cmd_pair_list(args: argparse.Namespace) -> int:
    from core.runtime.config import find_config_path, load_profile_with_env_override
    from core.runtime.inbound import PairingStore

    path = find_config_path(args.config)
    profile = load_profile_with_env_override(path)
    psp = profile.security.pairing_store_path
    if not psp:
        print("[pair] 未配置 security.pairing_store_path")
        return EXIT_CONFIG
    store = PairingStore(psp)
    rows = store.list_pairings()
    if not rows:
        print("[pair] 暂无配对记录")
        return EXIT_OK
    print(f"[pair] 共 {len(rows)} 条:\n")
    for r in sorted(rows, key=lambda x: (x.channel, x.sender_id)):
        print(f"  {r.channel}\t{r.sender_id}\t{r.trust_level}\t{r.paired_at}")
    return EXIT_OK


def cmd_plugins(args: argparse.Namespace) -> int:
    from core.runtime.plugin_host import PluginHost

    try:
        path = find_config_path(args.config)
        profile = load_and_validate_profile(path)
    except ConfigError as exc:
        print(f"[plugins] Config error: {exc}")
        return EXIT_CONFIG

    host = PluginHost(
        profile.plugins,
        profile.security,
        config_path=path,
        workspace=profile.workspace,
    )
    manifests = host.discover()

    if not manifests:
        print("[plugins] No plugins discovered.")
        return EXIT_OK

    print(f"[plugins] Discovered {len(manifests)} plugin(s):\n")
    for m in manifests:
        enabled = "✅" if (not profile.plugins.enabled_ids or m.id in profile.plugins.enabled_ids) else "⬜"
        print(f"  {enabled} {m.id} v{m.version} ({m.kind})")
        if m.metadata:
            name = m.metadata.get("name", "")
            desc = m.metadata.get("description", "")
            if name or desc:
                print(f"     {name}: {desc}")
    return EXIT_OK


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Hello-Agent CLI",
    )

    # Common options
    parser.add_argument("--config", metavar="PATH", default=None,
                        help="Override default config file path")
    parser.add_argument("--trace", choices=["human", "json"], default=None,
                        help="Trace output format")
    parser.add_argument("--trace-file", metavar="PATH", default=None,
                        help="Write trace output to file")
    parser.add_argument("--plugin-path", metavar="PATH", action="append",
                        default=None, help="Additional plugin search path (repeatable)")

    subs = parser.add_subparsers(dest="command")

    # task
    p_task = subs.add_parser("task", help="Run a single task (foreground)")
    p_task.add_argument("-m", "--message", required=True, help="Task message")
    p_task.add_argument("--no-tools", action="store_true", default=False,
                        help="Disable tool use")
    p_task.add_argument("--inbound-channel", default=None,
                        help="Simulate inbound source channel")
    p_task.add_argument("--inbound-sender", default=None,
                        help="Simulate inbound source sender ID")
    p_task.set_defaults(func=cmd_task)

    # chat
    p_chat = subs.add_parser("chat", help="Interactive conversation")
    p_chat.set_defaults(func=cmd_chat)

    # daemon
    p_daemon = subs.add_parser("daemon", help="Long-running loop (7×24)")
    p_daemon.set_defaults(func=cmd_daemon)

    # doctor
    p_doctor = subs.add_parser("doctor", help="Self-check (config, plugins, optional probe)")
    p_doctor.add_argument("--probe-mcp", action="store_true", default=False,
                          help="Probe MCP server connectivity")
    p_doctor.set_defaults(func=cmd_doctor)

    # health
    p_health = subs.add_parser("health", help="Health snapshot JSON")
    p_health.add_argument("--json", action="store_true", default=True,
                          help="Output as JSON (default)")
    p_health.set_defaults(func=cmd_health)

    # plugins
    p_plugins = subs.add_parser("plugins", help="List discovered/enabled plugins")
    p_plugins.add_argument(
        "action",
        nargs="?",
        default="list",
        choices=["list"],
        help="Plugin action (default: list)",
    )
    p_plugins.set_defaults(func=cmd_plugins)

    # telegram
    p_telegram = subs.add_parser("telegram", help="Telegram Bot 入站（长轮询）")
    t_sub = p_telegram.add_subparsers(dest="telegram_cmd", required=True)
    p_telegram_run = t_sub.add_parser("run", help="启动长轮询并处理文本消息")
    p_telegram_run.set_defaults(func=cmd_telegram_run)

    # pair
    p_pair = subs.add_parser("pair", help="入站来源配对（JSON 持久化）")
    pair_sub = p_pair.add_subparsers(dest="pair_cmd", required=True)
    p_pair_add = pair_sub.add_parser("add", help="添加配对")
    p_pair_add.add_argument("--channel", required=True, help="通道名，如 telegram")
    p_pair_add.add_argument("--sender-id", required=True, help="发送方 ID（字符串）")
    p_pair_add.add_argument(
        "--trust",
        choices=["full", "limited"],
        default="full",
        help="信任级别",
    )
    p_pair_add.set_defaults(func=cmd_pair_add)
    p_pair_remove = pair_sub.add_parser("remove", help="移除配对")
    p_pair_remove.add_argument("--channel", required=True)
    p_pair_remove.add_argument("--sender-id", required=True)
    p_pair_remove.set_defaults(func=cmd_pair_remove)
    p_pair_list = pair_sub.add_parser("list", help="列出配对")
    p_pair_list.set_defaults(func=cmd_pair_list)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return EXIT_CLI_USAGE

    return args.func(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ConfigError:
        sys.exit(EXIT_CONFIG)
    except Exception:
        sys.exit(EXIT_INTERNAL)
