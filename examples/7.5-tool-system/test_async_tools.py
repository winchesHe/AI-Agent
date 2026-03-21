# test_async_tools.py — 并行工具执行示例
from __future__ import annotations

import asyncio

import path_setup  # noqa: F401

from hello_agents import AsyncToolExecutor, ToolRegistry

from my_calculator_tool import create_calculator_registry


async def test_parallel_execution() -> None:
    registry = create_calculator_registry()
    executor = AsyncToolExecutor(registry)

    tasks = [
        {"tool_name": "my_calculator", "input_data": "2 + 2"},
        {"tool_name": "my_calculator", "input_data": "sqrt(16)"},
        {"tool_name": "my_calculator", "input_data": "10 * 5"},
    ]

    results = await executor.execute_tools_parallel(tasks)
    for i, result in enumerate(results):
        print(f"任务 {i + 1} 结果: {result}")
    executor.shutdown(wait=True)


if __name__ == "__main__":
    asyncio.run(test_parallel_execution())
