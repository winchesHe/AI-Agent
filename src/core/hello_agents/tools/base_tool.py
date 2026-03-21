"""工具抽象：统一名称、描述、参数自描述与执行入口。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from .tool_parameter import ToolParameter


class BaseTool(ABC):
    """具体工具需实现 `run`；名称与描述可在子类类属性或实例上提供。"""

    name: str = ""
    description: str = ""

    @abstractmethod
    def run(self, parameters: Dict[str, Any]) -> str:
        """根据解析后的参数字典执行工具并返回文本结果。"""
        ...

    def get_parameters(self) -> List[ToolParameter]:
        """默认单字符串参数 `input`；子类可覆盖以声明精确 schema。"""
        return [
            ToolParameter(
                name="input",
                type="string",
                description="工具的自然语言或结构化输入",
                required=True,
            )
        ]

    def to_openai_schema(self) -> Dict[str, Any]:
        """由 `get_parameters` 构建 OpenAI `tools` 条目。"""
        parameters = self.get_parameters()
        properties: Dict[str, Any] = {}
        required: List[str] = []

        for param in parameters:
            prop: Dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.default is not None:
                prop["description"] = (
                    f"{param.description} (默认: {param.default})"
                )
            if param.type == "array":
                prop["items"] = {"type": "string"}
            properties[param.name] = prop
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def openai_function_schema(self) -> Dict[str, Any]:
        """与 `FunctionCallAgent` / `ToolRegistry.openai_tools_payload` 兼容的别名。"""
        return self.to_openai_schema()


# 教材命名别名
Tool = BaseTool
