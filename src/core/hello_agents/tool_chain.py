"""工具链：按模板顺序调用已注册工具，用于组合能力。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .tool_registry import ToolRegistry


class ToolChain:
    """支持多个工具顺序执行；步骤输入支持 `{context_key}` 模板。"""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description
        self.steps: List[Dict[str, Any]] = []

    def add_step(
        self,
        tool_name: str,
        input_template: str,
        output_key: Optional[str] = None,
    ) -> None:
        self.steps.append(
            {
                "tool_name": tool_name,
                "input_template": input_template,
                "output_key": output_key or f"step_{len(self.steps)}_result",
            }
        )

    def execute(
        self,
        registry: ToolRegistry,
        initial_input: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        ctx: Dict[str, Any] = dict(context or {})
        ctx["input"] = initial_input

        print(f"🔗 开始执行工具链: {self.name}")

        for i, step in enumerate(self.steps, 1):
            tool_name = step["tool_name"]
            input_template = step["input_template"]
            output_key = step["output_key"]

            try:
                tool_input = input_template.format(**ctx)
            except KeyError as e:
                return f"❌ 工具链执行失败: 模板变量 {e} 未找到"

            preview = tool_input[:50] + ("..." if len(tool_input) > 50 else "")
            print(f"  步骤 {i}: 使用 {tool_name} 处理 '{preview}'")

            result = registry.execute_tool(tool_name, tool_input)
            ctx[output_key] = result

            print(f"  ✅ 步骤 {i} 完成，结果长度: {len(result)} 字符")

        final_key = self.steps[-1]["output_key"]
        final_result = str(ctx[final_key])
        print(f"🎉 工具链 '{self.name}' 执行完成")
        return final_result


class ToolChainManager:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry
        self.chains: Dict[str, ToolChain] = {}

    def register_chain(self, chain: ToolChain) -> None:
        self.chains[chain.name] = chain
        print(f"✅ 工具链 '{chain.name}' 已注册")

    def execute_chain(
        self,
        chain_name: str,
        input_data: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        if chain_name not in self.chains:
            return f"❌ 工具链 '{chain_name}' 不存在"
        return self.chains[chain_name].execute(self.registry, input_data, context)

    def list_chains(self) -> List[str]:
        return list(self.chains.keys())
