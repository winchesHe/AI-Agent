"""Self-diagnostics: structured health checks for support triage.

Implements FR-014 (self-check entry) and SC-007 (fault category distinction).
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from pydantic import BaseModel

from core.runtime.config import ConfigurationProfile
from core.runtime.plugin_host import (
    PluginHost,
    resolve_plugin_search_paths,
    resolve_workspace_roots,
)


class DiagnosticResult(BaseModel):
    """Single diagnostic outcome."""

    category: str
    ok: bool
    detail: str


class DoctorReport(BaseModel):
    """Aggregate doctor report."""

    python_version: str
    schema_version: str
    diagnostics: list[DiagnosticResult]
    overall_ok: bool

    def to_table(self) -> str:
        """Return a human-readable table of diagnostics."""
        lines: list[str] = []
        lines.append("[doctor] Self-check report")
        lines.append(f"  Python        : {self.python_version}")
        lines.append(f"  Schema version: {self.schema_version}")
        lines.append("")
        lines.append(f"  {'Category':<12} {'Status':<6} Detail")
        lines.append(f"  {'-'*12} {'-'*6} {'-'*40}")
        for d in self.diagnostics:
            status = "OK" if d.ok else "FAIL"
            lines.append(f"  {d.category:<12} {status:<6} {d.detail}")
        lines.append("")
        lines.append(f"  Overall: {'OK' if self.overall_ok else 'FAIL'}")
        return "\n".join(lines)

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return self.model_dump_json(indent=indent)


def run_doctor(
    profile: ConfigurationProfile,
    probe_mcp: bool = False,
    *,
    config_path: str | None = None,
) -> DoctorReport:
    """Run structured self-diagnostics against *profile*.

    Parameters
    ----------
    profile:
        The loaded configuration profile.
    probe_mcp:
        If ``True`` and MCP servers are configured, check that each
        server command is available on ``$PATH`` via :func:`shutil.which`.
    """
    diagnostics: list[DiagnosticResult] = []

    # -- config checks -------------------------------------------------------

    diagnostics.append(DiagnosticResult(
        category="config",
        ok=bool(profile.schema_version),
        detail=f"schema_version={'present' if profile.schema_version else 'missing'}",
    ))

    api_key_ref = profile.llm.api_key_ref
    key_set = bool(api_key_ref and os.getenv(api_key_ref))
    diagnostics.append(DiagnosticResult(
        category="config",
        ok=key_set,
        detail=f"env ${api_key_ref} {'set' if key_set else 'not set'}",
    ))

    model_ok = bool(profile.llm.model and profile.llm.model.strip())
    diagnostics.append(DiagnosticResult(
        category="config",
        ok=model_ok,
        detail=f"llm.model={'present' if model_ok else 'empty'}",
    ))

    # -- plugin checks -------------------------------------------------------

    resolved_paths = (
        resolve_plugin_search_paths(config_path, profile.plugins.search_paths)
        if config_path
        else list(profile.plugins.search_paths)
    )
    existing_paths: list[str] = []
    for sp in resolved_paths:
        exists = Path(sp).is_dir()
        if exists:
            existing_paths.append(sp)
        diagnostics.append(DiagnosticResult(
            category="plugins",
            ok=exists,
            detail=f"search_path '{sp}' {'exists' if exists else 'missing'}",
        ))

    if existing_paths and profile.plugins.enabled_ids:
        host = PluginHost(
            profile.plugins,
            profile.security,
            config_path=config_path,
            workspace=profile.workspace,
        )
        discovered = host.discover()
        discovered_ids = {m.id for m in discovered}
        for eid in profile.plugins.enabled_ids:
            found = eid in discovered_ids
            diagnostics.append(DiagnosticResult(
                category="plugins",
                ok=found,
                detail=f"enabled_id '{eid}' {'discovered' if found else 'not found in search_paths'}",
            ))

    # -- workspace (local filesystem tools) ---------------------------------

    if profile.workspace and profile.workspace.enabled and config_path:
        roots = resolve_workspace_roots(
            config_path, profile.workspace.allowed_roots,
        )
        if not profile.workspace.allowed_roots:
            diagnostics.append(DiagnosticResult(
                category="workspace",
                ok=False,
                detail="workspace.enabled but allowed_roots is empty — "
                       "local_workspace tools will not register",
            ))
        else:
            for rp in roots:
                exists = Path(rp).is_dir()
                diagnostics.append(DiagnosticResult(
                    category="workspace",
                    ok=exists,
                    detail=f"root '{rp}' {'exists' if exists else 'missing or not a directory'}",
                ))
    elif profile.workspace and profile.workspace.enabled and not config_path:
        diagnostics.append(DiagnosticResult(
            category="workspace",
            ok=False,
            detail="workspace enabled but config_path unknown — cannot resolve roots",
        ))

    # -- mcp checks ----------------------------------------------------------

    if probe_mcp and profile.mcp and profile.mcp.servers:
        for server in profile.mcp.servers:
            cmd_found = shutil.which(server.command) is not None
            diagnostics.append(DiagnosticResult(
                category="mcp",
                ok=cmd_found,
                detail=f"server '{server.name}' command '{server.command}' "
                       f"{'found' if cmd_found else 'not found on PATH'}",
            ))

    # -- build report --------------------------------------------------------

    return DoctorReport(
        python_version=sys.version,
        schema_version=profile.schema_version,
        diagnostics=diagnostics,
        overall_ok=all(d.ok for d in diagnostics),
    )
