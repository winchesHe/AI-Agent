"""示例 Tool 插件入口：保留 manifest 结构，不向注册表注册工具（原 echo 已移除）。"""
from __future__ import annotations

from typing import List

from core.hello_agents.tools.base_tool import BaseTool


def create_tool() -> List[BaseTool]:
    """工厂返回空列表：插件宿主会跳过注册，避免暴露回声类演示工具。"""
    return []
