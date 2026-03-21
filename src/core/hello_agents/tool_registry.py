"""工具注册表：Tool / 函数注册、描述聚合、按名执行、OpenAI tools 载荷。"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .tools.base_tool import BaseTool
from .tools.function_tool import CallableStringTool


def _string_input_to_params(tool: BaseTool, tool_input: str) -> Dict[str, Any]:
    """将 `execute_tool(..., tool_input: str)` 映射到工具声明的参数名。"""
    plist = tool.get_parameters()
    names = {p.name for p in plist}
    for key in ("query", "expression", "input"):
        if key in names:
            return {key: tool_input}
    required = [p for p in plist if p.required]
    if len(required) == 1:
        return {required[0].name: tool_input}
    if plist:
        return {plist[0].name: tool_input}
    return {"input": tool_input}


class ToolRegistry:
    """HelloAgents 工具注册表：支持 `BaseTool` 与 `register_function` 简便注册。"""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}
        self._functions: Dict[str, Dict[str, Any]] = {}

    def register_tool(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            print(f"⚠️ 警告: 工具 '{tool.name}' 已存在，将被覆盖。")
        self._tools[tool.name] = tool
        self._functions.pop(tool.name, None)
        print(f"✅ 工具 '{tool.name}' 已注册。")

    def register_function(
        self,
        name: str,
        description: str,
        func: Callable[[str], str],
    ) -> None:
        """
        直接注册 `Callable[[str], str]`，内部包装为 `CallableStringTool`。

        同时写入 `_functions` 以便与教材结构一致；执行以 `_tools` 为准。
        """
        if name in self._functions or name in self._tools:
            print(f"⚠️ 警告: 工具 '{name}' 已存在，将被覆盖。")

        self._functions[name] = {"description": description, "func": func}
        self._tools[name] = CallableStringTool(name, description, func)
        print(f"✅ 工具 '{name}' 已注册。")

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)
        self._functions.pop(name, None)

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    def get_tools_description(self) -> str:
        if not self._tools:
            return "暂无可用工具"
        lines = []
        for t in self._tools.values():
            lines.append(f"- {t.name}: {t.description}")
        return "\n".join(lines)

    def execute_tool(self, tool_name: str, tool_input: str) -> str:
        tool = self.get_tool(tool_name)
        if tool is None:
            return f"❌ 错误: 未找到工具 '{tool_name}'"
        params = _string_input_to_params(tool, tool_input)
        return tool.run(params)

    def openai_tools_payload(self) -> List[Dict[str, Any]]:
        """供 OpenAI `tools=` 使用的 schema 列表。"""
        return [t.openai_function_schema() for t in self._tools.values()]
