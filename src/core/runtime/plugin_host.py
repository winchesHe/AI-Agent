"""Plugin host: manifest discovery, validation, load ordering, and tool registry merging.

Implements plugin lifecycle management as specified in
specs/004-openclaw-alignment/contracts/plugin-manifest.schema.json.
"""
from __future__ import annotations

import importlib
import inspect
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from core.hello_agents.tool_registry import ToolRegistry
from core.hello_agents.tools.base_tool import BaseTool

from .config import PluginsConfig, SecurityConfig, WorkspaceConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ID pattern from the JSON schema
# ---------------------------------------------------------------------------

_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def resolve_plugin_search_paths(config_path: str, search_paths: list[str]) -> list[str]:
    """Resolve relative plugin *search_paths* against the config file directory.

    Running ``python src/main.py doctor`` uses the repo root as CWD; paths like
    ``../src/plugins`` in YAML would otherwise point outside the project. Relative
    entries are anchored to the directory containing *config_path* (e.g.
    ``assistant.yaml`` next to ``src/plugins`` → use ``src/plugins``).
    """
    base = Path(config_path).resolve().parent
    out: list[str] = []
    for sp in search_paths:
        p = Path(sp)
        if p.is_absolute():
            out.append(str(p.resolve()))
        else:
            out.append(str((base / p).resolve()))
    return out


def resolve_workspace_roots(config_path: str, roots: list[str]) -> list[Path]:
    """Resolve *roots* relative to the directory containing *config_path*."""
    base = Path(config_path).resolve().parent
    out: list[Path] = []
    for r in roots:
        p = Path(r)
        out.append(p.resolve() if p.is_absolute() else (base / p).resolve())
    return out


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class PluginLoadError(Exception):
    """Raised when a plugin entry point cannot be loaded."""


# ---------------------------------------------------------------------------
# Manifest model
# ---------------------------------------------------------------------------


class PluginManifest(BaseModel):
    """Pydantic model matching plugin-manifest.schema.json."""

    id: str
    version: str
    kind: Literal["tool", "skill", "subagent"]
    entry_point: Optional[str] = None
    permissions: List[Literal["read_only", "network", "mutating", "delegate"]] = Field(
        default_factory=list,
    )
    requires: List[str] = Field(default_factory=list)
    priority: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not _ID_PATTERN.match(v):
            raise ValueError(
                f"Plugin id '{v}' does not match pattern {_ID_PATTERN.pattern}"
            )
        return v


# ---------------------------------------------------------------------------
# Entry-point loader
# ---------------------------------------------------------------------------


def load_entry_point(entry_point: str) -> Any:
    """Import *module* and return *attr* from an ``"module:attr"`` string.

    Raises:
        PluginLoadError: If the format is invalid or the import fails.
    """
    if ":" not in entry_point:
        raise PluginLoadError(
            f"Invalid entry_point format '{entry_point}': expected 'module:attr'"
        )

    module_path, attr_name = entry_point.rsplit(":", 1)
    try:
        module = importlib.import_module(module_path)
    except Exception as exc:
        raise PluginLoadError(
            f"Cannot import module '{module_path}': {exc}"
        ) from exc

    try:
        return getattr(module, attr_name)
    except AttributeError as exc:
        raise PluginLoadError(
            f"Module '{module_path}' has no attribute '{attr_name}'"
        ) from exc


# ---------------------------------------------------------------------------
# Plugin load context (optional factory argument)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PluginLoadContext:
    """Passed to tool plugin factories that declare a single parameter."""

    config_path: str
    workspace: Optional[WorkspaceConfig] = None


def _invoke_tool_factory(
    factory: Any,
    context: Optional[PluginLoadContext],
) -> List[BaseTool]:
    """Call *factory* with no args, or with *context* if its signature accepts one."""
    if context is None:
        result = factory()
    else:
        try:
            sig = inspect.signature(factory)
            params = [
                p
                for p in sig.parameters.values()
                if p.kind
                not in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                )
            ]
        except (TypeError, ValueError):
            params = []

        if len(params) >= 1:
            result = factory(context)
        else:
            result = factory()

    if isinstance(result, BaseTool):
        return [result]
    if isinstance(result, (list, tuple)):
        tools: List[BaseTool] = []
        for item in result:
            if not isinstance(item, BaseTool):
                raise PluginLoadError(
                    f"Factory returned non-BaseTool entry: {type(item)!r}"
                )
            tools.append(item)
        return tools
    raise PluginLoadError(
        f"Factory must return BaseTool or sequence of BaseTool, got {type(result)!r}"
    )


# ---------------------------------------------------------------------------
# PluginHost
# ---------------------------------------------------------------------------


class PluginHost:
    """Discover, validate, and load plugins into a :class:`ToolRegistry`."""

    def __init__(
        self,
        plugins_config: PluginsConfig,
        security_config: SecurityConfig,
        *,
        config_path: str | None = None,
        workspace: Optional[WorkspaceConfig] = None,
    ) -> None:
        self._plugins_config = plugins_config
        self._security_config = security_config
        self._config_path = config_path
        self._workspace = workspace
        if config_path:
            self._search_paths = resolve_plugin_search_paths(
                config_path, plugins_config.search_paths
            )
        else:
            self._search_paths = list(plugins_config.search_paths)
        self._discovered: List[PluginManifest] = []
        self._loaded_ids: List[str] = []

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self) -> list[PluginManifest]:
        """Scan *search_paths* for plugin manifests and return validated list.

        * Skips directories without ``manifest.json`` or with invalid content.
        * Applies ``priority_overrides`` from config.
        * Sorts by priority descending (higher first).
        * Rejects duplicate ids (keeps the first occurrence).
        """
        manifests: List[PluginManifest] = []
        seen_ids: Dict[str, Path] = {}

        for search_path in self._search_paths:
            base = Path(search_path)
            if not base.is_dir():
                logger.warning("Plugin search path does not exist: %s", base)
                continue

            for child in sorted(base.iterdir()):
                if not child.is_dir():
                    continue
                manifest_file = child / "manifest.json"
                if not manifest_file.is_file():
                    continue

                # Parse & validate
                try:
                    raw = json.loads(manifest_file.read_text(encoding="utf-8"))
                    manifest = PluginManifest.model_validate(raw)
                except Exception as exc:
                    logger.warning(
                        "Skipping invalid plugin manifest %s: %s",
                        manifest_file,
                        exc,
                    )
                    continue

                # Duplicate detection
                if manifest.id in seen_ids:
                    logger.error(
                        "Duplicate plugin id '%s': %s conflicts with %s — skipping",
                        manifest.id,
                        manifest_file,
                        seen_ids[manifest.id],
                    )
                    continue

                # Apply priority override
                if manifest.id in self._plugins_config.priority_overrides:
                    manifest.priority = self._plugins_config.priority_overrides[
                        manifest.id
                    ]

                seen_ids[manifest.id] = manifest_file
                manifests.append(manifest)

        # Sort by priority descending
        manifests.sort(key=lambda m: m.priority, reverse=True)

        self._discovered = manifests
        return list(manifests)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_tools(self, registry: ToolRegistry) -> None:
        """Load discovered ``kind="tool"`` plugins and merge into *registry*.

        If ``enabled_ids`` is empty every discovered tool plugin is loaded;
        otherwise only plugins whose id appears in ``enabled_ids`` are loaded.

        Tool factories may take zero arguments, or one :class:`PluginLoadContext`
        argument. They must return a :class:`~core.hello_agents.tools.base_tool.BaseTool`
        or a sequence of such tools.
        """
        enabled = set(self._plugins_config.enabled_ids)
        load_ctx: Optional[PluginLoadContext] = None
        if self._config_path:
            load_ctx = PluginLoadContext(
                config_path=self._config_path,
                workspace=self._workspace,
            )

        for manifest in self._discovered:
            if manifest.kind != "tool":
                continue
            if enabled and manifest.id not in enabled:
                continue
            if not manifest.entry_point:
                logger.warning(
                    "Plugin '%s' has kind=tool but no entry_point — skipping",
                    manifest.id,
                )
                continue

            try:
                factory = load_entry_point(manifest.entry_point)
                tools = _invoke_tool_factory(factory, load_ctx)
                if not tools:
                    logger.warning(
                        "Plugin '%s' registered no tools — skipping id in loaded list",
                        manifest.id,
                    )
                    continue
                for tool in tools:
                    registry.register_tool(tool)
                self._loaded_ids.append(manifest.id)
            except PluginLoadError as exc:
                logger.error("Failed to load plugin '%s': %s", manifest.id, exc)
            except Exception as exc:
                logger.error(
                    "Unexpected error loading plugin '%s': %s", manifest.id, exc
                )

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_discovered(self) -> list[PluginManifest]:
        """Return the list of discovered manifests."""
        return list(self._discovered)

    def get_loaded_ids(self) -> list[str]:
        """Return ids of successfully loaded plugins."""
        return list(self._loaded_ids)

    def is_sensitive(self, plugin_id: str) -> bool:
        """Check if *plugin_id* is in ``security_config.sensitive_plugin_ids``."""
        return plugin_id in self._security_config.sensitive_plugin_ids
