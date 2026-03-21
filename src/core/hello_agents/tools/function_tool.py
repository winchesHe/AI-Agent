"""将 `Callable[[str], str]` 包装为 `BaseTool`，供 `register_function` 使用。"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .base_tool import BaseTool
from .tool_parameter import ToolParameter


class CallableStringTool(BaseTool):
    """接受 OpenAI 传入的参数字典，抽取字符串后交给底层函数。"""

    def __init__(self, name: str, description: str, func: Callable[[str], str]):
        self.name = name
        self.description = description
        self._func = func

    def run(self, parameters: Dict[str, Any]) -> str:
        if parameters.get("input") is not None:
            return self._func(str(parameters["input"]))
        for _k, v in parameters.items():
            if v is not None:
                return self._func(str(v))
        return self._func("")

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="input",
                type="string",
                description="工具输入字符串",
                required=True,
            )
        ]
