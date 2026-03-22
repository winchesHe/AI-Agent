"""在配置的 allowed_roots 内列出目录、读/写 UTF-8 文本文件。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from core.hello_agents.tools.base_tool import BaseTool
from core.hello_agents.tools.tool_parameter import ToolParameter
from core.runtime.config import WorkspaceConfig
from core.runtime.plugin_host import PluginLoadContext, resolve_workspace_roots


def _resolve_workspace_path(user_path: str, roots: List[Path]) -> Path:
    """Map *user_path* to a resolved path that stays under one of *roots*."""
    raw = Path(user_path)
    if raw.is_absolute():
        cand = raw.resolve()
        for r in roots:
            rr = r.resolve()
            try:
                cand.relative_to(rr)
                return cand
            except ValueError:
                continue
        raise ValueError("绝对路径不在 workspace.allowed_roots 任一目录下")
    for r in roots:
        rr = r.resolve()
        cand = (rr / raw).resolve()
        try:
            cand.relative_to(rr)
            return cand
        except ValueError:
            continue
    raise ValueError("相对路径解析后不在 workspace.allowed_roots 任一目录下")


def create_tools(ctx: PluginLoadContext) -> List[BaseTool]:
    """Plugin entry: no tools if workspace is off or roots empty."""
    ws = ctx.workspace
    if ws is None or not ws.enabled or not ws.allowed_roots:
        return []
    roots = resolve_workspace_roots(ctx.config_path, ws.allowed_roots)
    return [
        WorkspaceListDirTool(roots, ws),
        WorkspaceReadFileTool(roots, ws),
        WorkspaceWriteFileTool(roots, ws),
    ]


class _WorkspaceToolBase(BaseTool):
    roots: List[Path]
    _ws: WorkspaceConfig

    def __init__(self, roots: List[Path], ws: WorkspaceConfig) -> None:
        self.roots = roots
        self._ws = ws


class WorkspaceListDirTool(_WorkspaceToolBase):
    name = "workspace_list_dir"
    description = "列出允许工作区内的目录内容"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="目录路径（相对路径会依次在各 allowed_root 下解析，取首个合法位置）",
                required=True,
            ),
            ToolParameter(
                name="recursive",
                type="string",
                description="是否递归列出子目录（true/false，默认 false）",
                required=False,
                default="false",
            ),
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        path_s = str(parameters.get("path", ".")).strip() or "."
        rec_raw = parameters.get("recursive", "false")
        recursive = str(rec_raw).lower() in ("1", "true", "yes", "on")
        try:
            d = _resolve_workspace_path(path_s, self.roots)
        except ValueError as exc:
            return f"❌ {exc}"
        if not d.is_dir():
            return f"❌ 不是目录: {d}"
        lines: List[str] = []
        if recursive:
            for root, _dirnames, filenames in os.walk(d, topdown=True):
                rp = Path(root)
                rel = rp.relative_to(d)
                prefix = "" if rel == Path(".") else str(rel).replace("\\", "/") + "/"
                for name in sorted(filenames):
                    lines.append(f"{prefix}{name}")
        else:
            try:
                for entry in sorted(d.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                    kind = "dir" if entry.is_dir() else "file"
                    lines.append(f"{kind}:{entry.name}")
            except OSError as exc:
                return f"❌ 无法列出目录: {exc}"
        if not lines:
            return "(空目录)"
        head = lines[:500]
        out = "\n".join(head)
        if len(lines) > 500:
            out += "\n… 共省略（最多展示 500 行）"
        return out


class WorkspaceReadFileTool(_WorkspaceToolBase):
    name = "workspace_read_file"
    description = "读取允许工作区内的 UTF-8 文本文件"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="文件路径",
                required=True,
            ),
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        path_s = str(parameters.get("path", "")).strip()
        if not path_s:
            return "❌ path 不能为空"
        try:
            fpath = _resolve_workspace_path(path_s, self.roots)
        except ValueError as exc:
            return f"❌ {exc}"
        if not fpath.is_file():
            return f"❌ 不是文件: {fpath}"
        limit = max(256, self._ws.max_read_bytes)
        try:
            data = fpath.read_bytes()
        except OSError as exc:
            return f"❌ 读取失败: {exc}"
        if len(data) > limit:
            text = data[:limit].decode("utf-8", errors="replace")
            return (
                f"{text}\n\n… 已截断：文件 {len(data)} 字节，"
                f"超过 max_read_bytes={limit}"
            )
        return data.decode("utf-8", errors="replace")


class WorkspaceWriteFileTool(_WorkspaceToolBase):
    name = "workspace_write_file"
    description = "写入或覆盖允许工作区内的 UTF-8 文本文件"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="目标文件路径",
                required=True,
            ),
            ToolParameter(
                name="content",
                type="string",
                description="写入内容",
                required=True,
            ),
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        path_s = str(parameters.get("path", "")).strip()
        content = parameters.get("content")
        if content is None:
            return "❌ 缺少 content（请使用 JSON：path + content）"
        text = content if isinstance(content, str) else str(content)
        if not path_s:
            return "❌ path 不能为空"
        limit = max(256, self._ws.max_write_bytes)
        encoded = text.encode("utf-8")
        if len(encoded) > limit:
            return f"❌ 内容 {len(encoded)} 字节，超过 max_write_bytes={limit}"
        try:
            fpath = _resolve_workspace_path(path_s, self.roots)
        except ValueError as exc:
            return f"❌ {exc}"
        parent = fpath.parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return f"❌ 无法创建父目录: {exc}"
        try:
            fpath.write_text(text, encoding="utf-8")
        except OSError as exc:
            return f"❌ 写入失败: {exc}"
        return f"✅ 已写入 {fpath}（{len(encoded)} 字节）"
