"""在线程池中异步/并行执行同步工具（适合 I/O 型工具）。"""
from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Dict, List

from .tool_registry import ToolRegistry


class AsyncToolExecutor:
    def __init__(self, registry: ToolRegistry, max_workers: int = 4) -> None:
        self.registry = registry
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    async def execute_tool_async(self, tool_name: str, input_data: str) -> str:
        loop = asyncio.get_event_loop()

        def _execute() -> str:
            return self.registry.execute_tool(tool_name, input_data)

        return await loop.run_in_executor(self.executor, _execute)

    async def execute_tools_parallel(
        self, tasks: List[Dict[str, str]]
    ) -> List[str]:
        print(f"🚀 开始并行执行 {len(tasks)} 个工具任务")
        async_tasks = [
            self.execute_tool_async(t["tool_name"], t["input_data"]) for t in tasks
        ]
        results = await asyncio.gather(*async_tasks)
        print("✅ 所有工具任务执行完成")
        return list(results)

    def shutdown(self, wait: bool = True) -> None:
        self.executor.shutdown(wait=wait)

    def __del__(self) -> None:
        ex = getattr(self, "executor", None)
        if ex is not None:
            try:
                ex.shutdown(wait=False)
            except Exception:
                pass
