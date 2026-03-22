"""LoopDriver —— 包装 ReActAgent，提供预算控制与执行追踪。

对 ReActAgent.run() 进行薄封装：
- 墙钟超时检测（wall-clock timeout）
- 自动生成 AssistantRunTrace（thought → final / error）
- 返回结构化 LoopResult
"""

from __future__ import annotations

import time
from typing import Callable, Optional

from pydantic import BaseModel, Field

from core.hello_agents.react_agent import ReActAgent
from core.hello_agents.tool_registry import ToolRegistry
from core.llm.llm_client import HelloAgentsLLM

from .config import LoopConfig
from .trace import AssistantRunTrace, TraceStep, new_trace


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


class LoopResult(BaseModel):
    """LoopDriver 单次运行的结构化结果。"""

    answer: str = Field(description="最终回答文本")
    trace: AssistantRunTrace = Field(description="本次运行的追踪记录")
    success: bool = Field(description="是否正常完成")
    error: Optional[str] = Field(default=None, description="失败时的错误信息")


# ---------------------------------------------------------------------------
# LoopDriver
# ---------------------------------------------------------------------------


class LoopDriver:
    """预算感知的 Agent 运行驱动器。

    内部创建 :class:`ReActAgent` 并在其 ``run()`` 前后注入追踪步骤与
    墙钟超时检测。
    """

    def __init__(
        self,
        llm: HelloAgentsLLM,
        tool_registry: ToolRegistry,
        loop_config: LoopConfig,
        parent_run_id: str | None = None,
        depth: int = 0,
    ) -> None:
        self.llm = llm
        self.tool_registry = tool_registry
        self.loop_config = loop_config
        self.parent_run_id = parent_run_id
        self.depth = depth

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def run(
        self,
        user_input: str,
        *,
        no_tools: bool = False,
        on_trace_step: Optional[Callable[[TraceStep], None]] = None,
        on_llm_stream: Optional[Callable[[int, str, str], None]] = None,
    ) -> LoopResult:
        """执行一次 Agent Loop 并返回 :class:`LoopResult`。

        Parameters
        ----------
        user_input:
            用户输入文本。
        no_tools:
            若为 ``True``，则使用空的 ToolRegistry（纯推理模式）。
        on_trace_step:
            每条 trace 步骤写入后调用（如 IM 流式展示推理/工具过程）。
        on_llm_stream:
            模型 **token 流** 观测：``(step, text, phase)``。
            ``phase`` 为 ``"step_start"`` / ``"delta"`` / ``"end"``；
            ``text`` 为当前步累积全文（``step_start`` 时为空）。
        """
        trace = new_trace(
            parent_run_id=self.parent_run_id,
            depth=self.depth,
            on_step=on_trace_step,
        )

        # 运行起点（后续每步由 ReActAgent 写入 thought / tool_* / mcp_*）
        trace.add_step("thought", {"phase": "run_start", "user_input": user_input})

        registry = ToolRegistry() if no_tools else self.tool_registry

        agent = ReActAgent(
            name="loop-agent",
            llm=self.llm,
            tool_registry=registry,
            max_steps=self.loop_config.max_iterations,
        )

        start = time.monotonic()
        try:
            answer = agent.run(
                user_input,
                trace=trace,
                llm_stream_callback=on_llm_stream,
            )
            elapsed = time.monotonic() - start

            if elapsed > self.loop_config.max_wall_seconds:
                trace.add_step(
                    "error",
                    {
                        "error_class": "TimeoutError",
                        "message": (
                            f"Wall-clock timeout: {elapsed:.1f}s "
                            f"exceeded limit {self.loop_config.max_wall_seconds}s"
                        ),
                    },
                )
                return LoopResult(
                    answer=answer,
                    trace=trace,
                    success=False,
                    error=(
                        f"Wall-clock timeout: {elapsed:.1f}s "
                        f"exceeded limit {self.loop_config.max_wall_seconds}s"
                    ),
                )

            trace.add_step("final", {"answer": answer})
            return LoopResult(
                answer=answer,
                trace=trace,
                success=True,
            )

        except Exception as exc:
            trace.add_step(
                "error",
                {
                    "error_class": type(exc).__name__,
                    "message": str(exc),
                },
            )
            return LoopResult(
                answer="",
                trace=trace,
                success=False,
                error=str(exc),
            )
