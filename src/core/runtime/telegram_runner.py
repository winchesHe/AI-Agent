"""Telegram Bot 入站：长轮询 + LoopDriver（specs/005-telegram-im）。"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from typing import TYPE_CHECKING

from core.runtime.config import ConfigError, ConfigurationProfile
from core.runtime.loop_driver import LoopResult
from core.runtime.trace import TraceStep

if TYPE_CHECKING:
    from core.hello_agents.tool_registry import ToolRegistry
    from core.llm.llm_client import HelloAgentsLLM

logger = logging.getLogger(__name__)

_TELEGRAM_MAX_MESSAGE_LEN = 4000


def _thread_send_kwargs(message: object) -> dict:
    """论坛超级群话题：出站消息须带 message_thread_id，否则会落到错误分区。"""
    tid = getattr(message, "message_thread_id", None)
    if tid is None:
        return {}
    try:
        return {"message_thread_id": int(tid)}
    except (TypeError, ValueError):
        return {}


def _truncate_for_telegram(text: str, max_len: int = _TELEGRAM_MAX_MESSAGE_LEN) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 24].rstrip() + "\n…(已截断)"


def _format_trace_line_for_im(step: TraceStep) -> str:
    """将单条 trace 步骤格式化为 IM 可读一行（对齐 trace-event 种类）。"""

    payload = step.payload or {}
    kind = step.kind

    if kind == "thought":
        if payload.get("phase") == "run_start":
            return "📥 已收到，正在连接模型…"
        sn = payload.get("step")
        th = (payload.get("thought") or "").strip().replace("\n", " ")
        if th:
            clip = th[:280] + ("…" if len(th) > 280 else "")
            return f"💭 第{sn}步：{clip}"
        return f"💭 第{sn}步 · 推理中…"

    if kind == "tool_call":
        name = payload.get("tool_name") or "?"
        return f"🔧 第{payload.get('step')}步：调用工具 `{name}`"

    if kind == "tool_result":
        name = payload.get("tool_name") or "?"
        obs = (payload.get("observation_preview") or "").strip().replace("\n", " ")
        if obs:
            clip = obs[:200] + ("…" if len(obs) > 200 else "")
            return f"📥 `{name}`：{clip}"
        return f"📥 `{name}` 已返回"

    if kind == "mcp_call":
        name = payload.get("tool_name") or "?"
        return f"🌐 第{payload.get('step')}步：MCP `{name}`"

    if kind == "mcp_result":
        name = payload.get("tool_name") or "?"
        obs = (payload.get("observation_preview") or "").strip().replace("\n", " ")
        if obs:
            clip = obs[:200] + ("…" if len(obs) > 200 else "")
            return f"📥 MCP `{name}`：{clip}"
        return f"📥 MCP `{name}` 完成"

    if kind == "skill_activate":
        return f"📜 技能：{payload.get('skill_id', '?')}"

    if kind == "subagent_delegate":
        return "🧩 委派子代理…"

    if kind == "subagent_result":
        return "🧩 子代理已返回"

    if kind == "error":
        msg = (payload.get("message") or "").strip()
        return f"❌ {msg[:400]}"

    if kind == "final":
        return "✅ 本轮推理结束，正在发送回答…"

    return ""


def _progress_message_text(lines: list[str]) -> str:
    body = "\n".join(lines) if lines else "（等待模型…）"
    return _truncate_for_telegram(f"🔄 运行进度\n\n{body}", max_len=_TELEGRAM_MAX_MESSAGE_LEN)


def _combined_progress_text(
    lines: list[str],
    stream_step: int,
    stream_text: str,
) -> str:
    """轨迹行 + 当前 ReAct 步的模型流式输出（单条消息内合并）。"""

    if stream_step <= 0:
        return _progress_message_text(lines)

    body_lines = "\n".join(lines) if lines else "（尚无步骤）"
    st = stream_text.strip()
    if not st:
        stream_body = "（等待首个 token…）"
    else:
        stream_body = st
    combined = (
        "🔄 运行进度\n\n"
        f"{body_lines}\n\n"
        f"📝 第{stream_step}步 · 模型输出\n"
        f"{stream_body}"
    )
    return _truncate_for_telegram(combined, max_len=_TELEGRAM_MAX_MESSAGE_LEN)


def _loop_result_to_user_text(result: LoopResult) -> str:
    """Turn LoopDriver result into a non-empty string for Telegram (API rejects empty body)."""

    if result.success:
        body = (result.answer or "").strip()
        if body:
            return result.answer
        return (
            "助理已结束本轮，但未生成可见文本（例如模型给出了空的 Finish）。"
            "请换种说法重试。"
        )

    err = (result.error or "").strip()
    ans = (result.answer or "").strip()
    if err and ans:
        return f"处理未完成。\n\n原因：{err}\n\n已返回内容：{ans}"
    if err:
        return f"处理失败：{err}"
    if ans:
        return ans
    return "处理失败，未返回具体原因，请稍后重试或查看服务端日志。"


async def _reply_safe(
    text: str,
    *,
    reply_target: object,
    thread_hint: object | None = None,
) -> None:
    """Send *text* as a reply to *reply_target* (thread chain under progress).

    *thread_hint* supplies ``message_thread_id`` for forum topics when *reply_target*
    might omit it (typically the user's inbound message).
    """
    from telegram.error import TelegramError

    reply = _truncate_for_telegram((text or "").strip())
    if not reply:
        reply = "未生成有效回复，请稍后重试。"

    reply_fn = getattr(reply_target, "reply_text", None)
    if reply_fn is None:
        logger.error("telegram reply_target has no reply_text")
        return

    src = thread_hint if thread_hint is not None else reply_target
    extra = _thread_send_kwargs(src)

    try:
        await reply_fn(reply, **extra)
    except TelegramError as exc:
        logger.exception("Telegram reply_text failed: %s", exc)
        short = f"无法发送完整回复（{type(exc).__name__}）。请查看日志或缩短问题后重试。"
        try:
            await reply_fn(_truncate_for_telegram(short, max_len=500), **extra)
        except Exception:
            logger.exception("Telegram fallback reply also failed")
    except Exception as exc:
        logger.exception("Unexpected error sending Telegram reply: %s", exc)
        try:
            await reply_fn(
                _truncate_for_telegram(
                    f"回复发送异常（{type(exc).__name__}），任务可能已执行。",
                    max_len=500,
                ),
                **extra,
            )
        except Exception:
            logger.exception("Telegram fallback reply also failed")


def run_telegram_polling(
    profile: ConfigurationProfile,
    llm: "HelloAgentsLLM",
    registry: "ToolRegistry",
) -> None:
    """阻塞运行 Telegram 长轮询直至进程收到停止信号。"""
    try:
        from telegram.ext import (
            Application,
            CommandHandler,
            ContextTypes,
            MessageHandler,
            filters,
        )
    except ImportError as exc:
        raise ConfigError(
            "未安装 python-telegram-bot，请执行: pip install 'python-telegram-bot>=21.0'",
            field="telegram",
        ) from exc

    tg = profile.telegram
    if tg is None or not tg.enabled:
        raise ConfigError(
            "请在配置中设置 telegram.enabled: true 及 telegram 段",
            field="telegram.enabled",
        )

    ref = (tg.bot_token_ref or "TELEGRAM_BOT_TOKEN").strip()
    token = os.getenv(ref, "").strip()
    if not token:
        raise ConfigError(
            f"环境变量 '{ref}' 未设置或为空（Bot Token）",
            field="telegram.bot_token_ref",
        )

    from core.runtime.inbound import AccessDeniedError, InboundGate, InboundSource, PairingStore
    from core.runtime.loop_driver import LoopDriver

    store = PairingStore(profile.security.pairing_store_path)
    gate = InboundGate(profile.security, store)
    driver = LoopDriver(
        llm=llm,
        tool_registry=registry,
        loop_config=profile.loop,
    )

    async def handle_text(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        from telegram.error import BadRequest, TelegramError

        message = getattr(update, "message", None)
        user = getattr(update, "effective_user", None)
        if message is None or user is None:
            return
        text = getattr(message, "text", None) or ""
        if not text.strip():
            await message.reply_text("请发送文本消息。", **_thread_send_kwargs(message))
            return

        source = InboundSource(channel="telegram", sender_id=str(user.id))

        for pid in profile.security.sensitive_plugin_ids:
            try:
                gate.enforce(source, pid)
            except AccessDeniedError:
                await message.reply_text(
                    "当前账号未配对或无权使用受限能力。请让管理员执行："
                    f" pair add --channel telegram --sender-id {user.id}",
                    **_thread_send_kwargs(message),
                )
                return

        loop = asyncio.get_running_loop()
        status_msg = await message.reply_text(
            "🔄 已收到，准备运行…",
            **_thread_send_kwargs(message),
        )

        lines_lock = threading.Lock()
        progress_lines: list[str] = []
        stream_state = {"step": 0, "text": ""}
        edit_lock = asyncio.Lock()
        throttle_lock = threading.Lock()
        last_flush = [0.0]
        _STREAM_MIN_INTERVAL = 0.35

        async def _apply_combined_edit() -> None:
            async with edit_lock:
                with lines_lock:
                    snap = list(progress_lines)
                    st_step = stream_state["step"]
                    st_text = stream_state["text"]
                body = _combined_progress_text(snap, st_step, st_text)
                try:
                    await status_msg.edit_text(body)
                except BadRequest as exc:
                    if "message is not modified" in str(exc).lower():
                        return
                    logger.warning("Telegram progress edit BadRequest: %s", exc)
                except TelegramError as exc:
                    logger.warning("Telegram progress edit failed: %s", exc)

        def _schedule_combined(*, force: bool) -> None:
            now = time.monotonic()
            if not force:
                with throttle_lock:
                    if now - last_flush[0] < _STREAM_MIN_INTERVAL:
                        return
            with throttle_lock:
                last_flush[0] = now
            asyncio.run_coroutine_threadsafe(_apply_combined_edit(), loop)

        def _on_trace_step(step: TraceStep) -> None:
            line = _format_trace_line_for_im(step)
            with lines_lock:
                if line:
                    progress_lines.append(line)
            _schedule_combined(force=True)

        def _on_llm_stream(step: int, text: str, phase: str) -> None:
            with lines_lock:
                stream_state["step"] = max(1, step)
                if phase == "step_start":
                    stream_state["text"] = ""
                else:
                    stream_state["text"] = text
            _schedule_combined(force=phase in ("step_start", "end"))

        def _run_agent() -> LoopResult:
            return driver.run(
                text,
                on_trace_step=_on_trace_step,
                on_llm_stream=_on_llm_stream,
            )

        try:
            result = await asyncio.to_thread(_run_agent)
        except Exception:
            logger.exception("LoopDriver failed for telegram user %s", user.id)
            err_plain = "内部错误，请稍后重试。详情已写入日志。"
            err_edit = _truncate_for_telegram(f"❌ {err_plain}", max_len=500)
            try:
                await status_msg.edit_text(err_edit)
            except Exception:
                logger.exception("Failed to edit status after LoopDriver error")
                await _reply_safe(
                    err_plain,
                    reply_target=status_msg,
                    thread_hint=message,
                )
            return

        if result.success:
            footer = "✅ 本轮已完成，回答已回复在本进度消息下方。"
        else:
            footer = "⚠️ 本轮未完全成功，说明已回复在本进度消息下方。"
        try:
            await status_msg.edit_text(_truncate_for_telegram(footer, max_len=500))
        except Exception:
            logger.debug("final status edit skipped", exc_info=True)

        await _reply_safe(
            _loop_result_to_user_text(result),
            reply_target=status_msg,
            thread_hint=message,
        )

    async def handle_start(update: object, _context: ContextTypes.DEFAULT_TYPE) -> None:
        message = getattr(update, "message", None)
        if message:
            await message.reply_text(
                "Hello-Agent 已连接。直接发送文本即可对话。",
                **_thread_send_kwargs(message),
            )

    app = (
        Application.builder()
        .token(token)
        .build()
    )
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Telegram bot polling started (press Ctrl+C to stop)")
    app.run_polling(allowed_updates=["message"])
