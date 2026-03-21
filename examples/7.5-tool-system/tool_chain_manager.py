# tool_chain_manager.py — 教材 7.5.4 工具链示例
from __future__ import annotations

import path_setup  # noqa: F401

from hello_agents import SearchTool, ToolChain, ToolChainManager, ToolRegistry

from my_calculator_tool import create_calculator_registry


def create_research_chain() -> ToolChain:
    """研究工具链示例：搜索 -> 将结果交给计算器（演示模板串联）。"""
    chain = ToolChain(
        name="research_and_calculate",
        description="搜索信息并进行相关计算",
    )

    chain.add_step(
        tool_name="search",
        input_template="{input}",
        output_key="search_result",
    )

    chain.add_step(
        tool_name="my_calculator",
        input_template="1+1",
        output_key="calculation_result",
    )

    return chain


if __name__ == "__main__":
    registry = create_calculator_registry()
    registry.register_tool(SearchTool())

    manager = ToolChainManager(registry)
    manager.register_chain(create_research_chain())

    out = manager.execute_chain(
        "research_and_calculate",
        "Python 3.12 新特性",
    )
    print("链输出摘要（末步）:\n", out[:500], "...")
