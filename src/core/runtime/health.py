"""Health snapshot: runtime health checks and reporting.

Implements the schema defined in specs/004-openclaw-alignment/contracts/health-snapshot.schema.json.
"""
from __future__ import annotations

import os
import time
from typing import Literal

from pydantic import BaseModel

from core.runtime.config import ConfigurationProfile
from core.runtime.plugin_host import resolve_plugin_search_paths


class CheckResult(BaseModel):
    """Single health-check outcome."""

    ok: bool
    detail: str = ""


class HealthSnapshot(BaseModel):
    """Aggregate health snapshot returned by the ``health`` subcommand."""

    model_config = {"extra": "forbid"}

    status: Literal["ok", "degraded", "unhealthy"]
    uptime_seconds: float = 0.0
    loaded_plugins: list[str] = []
    checks: dict[str, CheckResult] = {}

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return self.model_dump_json(indent=indent)


def build_health_snapshot(
    profile: ConfigurationProfile,
    start_time: float | None = None,
    loaded_plugin_ids: list[str] | None = None,
    *,
    config_path: str | None = None,
) -> HealthSnapshot:
    """Build a :class:`HealthSnapshot` by running health checks.

    Parameters
    ----------
    profile:
        The loaded configuration profile.
    start_time:
        A ``time.monotonic()`` timestamp captured at process start.
        Used to calculate *uptime_seconds*.
    loaded_plugin_ids:
        List of plugin identifiers currently loaded.
    """

    # -- individual checks ---------------------------------------------------
    config_loaded = CheckResult(ok=True, detail="profile loaded")

    api_key_ref = profile.llm.api_key_ref
    llm_key_set = CheckResult(
        ok=bool(os.getenv(api_key_ref)),
        detail=f"env ${api_key_ref} {'set' if os.getenv(api_key_ref) else 'not set'}",
    )

    plugin_paths = (
        resolve_plugin_search_paths(config_path, profile.plugins.search_paths)
        if config_path
        else list(profile.plugins.search_paths)
    )
    any_path_exists = any(os.path.isdir(p) for p in plugin_paths)
    plugins_path_exists = CheckResult(
        ok=any_path_exists,
        detail="at least one search_path exists" if any_path_exists else "no search_path found on disk",
    )

    checks: dict[str, CheckResult] = {
        "config_loaded": config_loaded,
        "llm_key_set": llm_key_set,
        "plugins_path_exists": plugins_path_exists,
    }

    # -- derive overall status -----------------------------------------------
    if all(c.ok for c in checks.values()):
        status: Literal["ok", "degraded", "unhealthy"] = "ok"
    elif not llm_key_set.ok:
        status = "unhealthy"
    else:
        status = "degraded"

    # -- uptime --------------------------------------------------------------
    uptime = (time.monotonic() - start_time) if start_time is not None else 0.0

    return HealthSnapshot(
        status=status,
        uptime_seconds=uptime,
        loaded_plugins=loaded_plugin_ids or [],
        checks=checks,
    )
