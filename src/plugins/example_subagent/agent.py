"""示例 SubAgent 插件入口。"""
from __future__ import annotations

from core.runtime.subagent import SubAgentDefinition


def create_subagent() -> SubAgentDefinition:
    return SubAgentDefinition(
        id="example-subagent",
        tool_allowlist=["search"],
        max_iterations=3,
        can_delegate=False,
    )
