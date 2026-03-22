"""示例 Tool 插件入口：注册一个简单的 echo 工具。"""
from __future__ import annotations

from typing import Any, Dict, List

from core.hello_agents.tools.base_tool import BaseTool
from core.hello_agents.tools.tool_parameter import ToolParameter


class EchoTool(BaseTool):
    """回声工具 —— 将输入原样返回，用于冒烟测试。"""

    name = "echo"
    description = "回声工具：将输入原样返回（用于冒烟测试）。"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="input",
                type="string",
                description="任意文本",
                required=True,
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        text = parameters.get("input", "")
        return f"[echo] {text}"


def create_tool() -> BaseTool:
    """Plugin entry point: return a BaseTool instance."""
    return EchoTool()
