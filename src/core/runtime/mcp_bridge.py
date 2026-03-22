"""MCP stdio client bridge — maps remote MCP tools to local BaseTool adapters.

Launches MCP servers as stdio subprocesses, discovers their tool lists
(with TTL caching), and exposes each remote tool via :class:`MCPToolAdapter`
which conforms to the :class:`BaseTool` interface.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from core.hello_agents.tool_registry import ToolRegistry
from core.hello_agents.tools.base_tool import BaseTool
from core.hello_agents.tools.tool_parameter import ToolParameter
from core.runtime.config import MCPConfig, MCPServerConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional MCP SDK import
# ---------------------------------------------------------------------------

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    _MCP_AVAILABLE = True
except Exception:  # ImportError or ModuleNotFoundError
    _MCP_AVAILABLE = False


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class MCPError(Exception):
    """MCP-related error.

    Attributes:
        error_class: ``"transport"`` for connection / protocol failures,
                     ``"business"`` when the remote tool returned an error.
    """

    def __init__(self, message: str, *, error_class: str = "transport") -> None:
        super().__init__(message)
        self.error_class = error_class


# ---------------------------------------------------------------------------
# Tool adapter
# ---------------------------------------------------------------------------


class MCPToolAdapter(BaseTool):
    """Wraps a single remote MCP tool so it satisfies the local ``BaseTool`` API.

    The naming convention is ``mcp__{server_name}__{tool_name}`` so that each
    tool is uniquely identifiable even when multiple servers expose tools with
    the same name.
    """

    source: str = "mcp"

    def __init__(
        self,
        server_name: str,
        tool_name: str,
        tool_description: str,
        input_schema: Dict[str, Any],
        bridge: MCPBridge,
    ) -> None:
        self.name = f"mcp__{server_name}__{tool_name}"
        self.description = tool_description or ""
        self._server_name = server_name
        self._tool_name = tool_name
        self._input_schema = input_schema
        self._bridge = bridge

    # -- BaseTool interface --------------------------------------------------

    def get_parameters(self) -> List[ToolParameter]:
        """Build parameter list from the remote tool's JSON Schema."""
        properties: Dict[str, Any] = self._input_schema.get("properties", {})
        required_set: set[str] = set(self._input_schema.get("required", []))

        params: List[ToolParameter] = []
        for prop_name, prop_def in properties.items():
            params.append(
                ToolParameter(
                    name=prop_name,
                    type=prop_def.get("type", "string"),
                    description=prop_def.get("description", ""),
                    required=prop_name in required_set,
                    default=prop_def.get("default"),
                )
            )
        return params or super().get_parameters()

    def run(self, parameters: Dict[str, Any]) -> str:
        """Synchronous wrapper — runs ``call_tool`` on the current event loop."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            # Already inside an async context — schedule via a new thread to
            # avoid deadlocking the running loop.
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    asyncio.run,
                    self._bridge.call_tool(
                        self._server_name, self._tool_name, parameters,
                    ),
                )
                return future.result()

        return asyncio.run(
            self._bridge.call_tool(self._server_name, self._tool_name, parameters),
        )


# ---------------------------------------------------------------------------
# Bridge
# ---------------------------------------------------------------------------

# Internal per-server bookkeeping
class _ServerState:
    """Holds runtime state for a single MCP server connection."""

    __slots__ = ("config", "session", "context", "tools_cache", "cache_ts")

    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self.session: Any = None  # mcp.ClientSession when connected
        self.context: Any = None  # async context manager for stdio transport
        self.tools_cache: List[Any] = []
        self.cache_ts: float = 0.0


class MCPBridge:
    """Manages MCP server connections and exposes their tools locally.

    Usage::

        bridge = MCPBridge(profile.mcp)
        await bridge.connect_all()
        tools = bridge.get_tools()        # list[MCPToolAdapter]
        result = await bridge.call_tool("my-server", "my-tool", {"q": "hi"})
        await bridge.close_all()
    """

    def __init__(self, mcp_config: MCPConfig | None) -> None:
        self._servers: Dict[str, _ServerState] = {}
        if mcp_config:
            for srv in mcp_config.servers:
                self._servers[srv.name] = _ServerState(srv)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect_all(self) -> None:
        """Start each configured MCP server subprocess and cache its tools."""
        if not self._servers:
            logger.debug("MCPBridge: no servers configured — nothing to connect.")
            return

        if not _MCP_AVAILABLE:
            raise MCPError(
                "The 'mcp' package is not installed. "
                "Install it with: pip install 'mcp>=1.0.0'",
                error_class="transport",
            )

        for name, state in self._servers.items():
            try:
                await self._connect_server(state)
                logger.info("MCP server '%s' connected (%d tools).", name, len(state.tools_cache))
            except Exception as exc:
                logger.error("Failed to connect MCP server '%s': %s", name, exc)
                raise MCPError(
                    f"Failed to connect MCP server '{name}': {exc}",
                    error_class="transport",
                ) from exc

    async def close_all(self) -> None:
        """Terminate all MCP server subprocesses."""
        for name, state in self._servers.items():
            try:
                if state.context is not None:
                    await state.context.__aexit__(None, None, None)
                    state.context = None
                    state.session = None
                    logger.debug("MCP server '%s' closed.", name)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error closing MCP server '%s': %s", name, exc)

    # ------------------------------------------------------------------
    # Tool discovery
    # ------------------------------------------------------------------

    def get_tools(self) -> List[MCPToolAdapter]:
        """Return a flat list of :class:`MCPToolAdapter` for every discovered tool."""
        adapters: List[MCPToolAdapter] = []
        for name, state in self._servers.items():
            for tool in state.tools_cache:
                adapters.append(
                    MCPToolAdapter(
                        server_name=name,
                        tool_name=tool.name,
                        tool_description=getattr(tool, "description", "") or "",
                        input_schema=getattr(tool, "inputSchema", {}) or {},
                        bridge=self,
                    )
                )
        return adapters

    # ------------------------------------------------------------------
    # Tool invocation
    # ------------------------------------------------------------------

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> str:
        """Invoke a remote MCP tool and return the text result.

        Raises:
            MCPError: On transport failure or when the tool signals an error.
        """
        if not _MCP_AVAILABLE:
            raise MCPError(
                "The 'mcp' package is not installed.",
                error_class="transport",
            )

        state = self._servers.get(server_name)
        if state is None:
            raise MCPError(
                f"Unknown MCP server: '{server_name}'",
                error_class="transport",
            )

        session: ClientSession = state.session
        if session is None:
            raise MCPError(
                f"MCP server '{server_name}' is not connected.",
                error_class="transport",
            )

        try:
            result = await session.call_tool(tool_name, arguments=arguments)
        except Exception as exc:
            raise MCPError(
                f"Transport error calling '{tool_name}' on '{server_name}': {exc}",
                error_class="transport",
            ) from exc

        # The MCP SDK returns a CallToolResult with .content list and .isError flag.
        if getattr(result, "isError", False):
            text = _extract_text(result)
            raise MCPError(
                f"Tool '{tool_name}' returned an error: {text}",
                error_class="business",
            )

        return _extract_text(result)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _connect_server(self, state: _ServerState) -> None:
        """Open a stdio transport to a single MCP server and cache its tools."""
        cfg = state.config
        params = StdioServerParameters(
            command=cfg.command,
            args=cfg.args,
            env=cfg.env or None,
        )

        # stdio_client is an async context manager that yields (read, write).
        ctx = stdio_client(params)
        read_stream, write_stream = await ctx.__aenter__()
        state.context = ctx

        session = ClientSession(read_stream, write_stream)
        await session.initialize()
        state.session = session

        await self._refresh_tools(state)

    async def _refresh_tools(self, state: _ServerState) -> None:
        """Fetch (or re-fetch) the tool list for *state*, respecting TTL."""
        now = time.monotonic()
        ttl = state.config.tools_list_ttl_seconds
        if state.tools_cache and (now - state.cache_ts) < ttl:
            return  # cache still valid

        result = await state.session.list_tools()
        state.tools_cache = list(result.tools)
        state.cache_ts = now


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _extract_text(result: Any) -> str:
    """Pull plain-text from a ``CallToolResult.content`` list."""
    parts: list[str] = []
    for item in getattr(result, "content", []):
        if hasattr(item, "text"):
            parts.append(item.text)
        else:
            parts.append(str(item))
    return "\n".join(parts) if parts else ""


def connect_mcp_tools_sync(
    mcp_config: MCPConfig | None,
    registry: ToolRegistry,
) -> Optional[MCPBridge]:
    """Connect MCP servers and register :class:`MCPToolAdapter` tools on *registry*.

    Returns the :class:`MCPBridge` so the caller can :meth:`MCPBridge.close_all`
    when done. Returns ``None`` if there are no servers. On failure, logs a
    warning and returns ``None`` (assistant still runs with non-MCP tools).
    """
    if not mcp_config or not mcp_config.servers:
        return None

    bridge = MCPBridge(mcp_config)

    async def _setup() -> MCPBridge:
        await bridge.connect_all()
        for t in bridge.get_tools():
            registry.register_tool(t)
        return bridge

    try:
        return asyncio.run(_setup())
    except MCPError as exc:
        logger.warning("MCP setup skipped: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("MCP setup failed: %s", exc)
        return None
