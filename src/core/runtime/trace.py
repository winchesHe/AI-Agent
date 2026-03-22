"""执行追踪模型 —— 对齐 trace-event.schema.json 契约。

提供 `TraceStep` 与 `AssistantRunTrace` 两个 Pydantic v2 模型，
用于记录 Agent Loop 每轮的推理步骤（thought / tool_call / error …）。

安全约定
--------
**payload 中禁止包含 API Key、Token 等敏感信息。**
调用方应在写入 payload 前自行脱敏。
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Callable, Dict, List, Literal, Optional

logger = logging.getLogger(__name__)

from pydantic import BaseModel, Field

# ---------- 常量 ----------

StepKind = Literal[
    "thought",
    "tool_call",
    "tool_result",
    "skill_activate",
    "mcp_call",
    "mcp_result",
    "subagent_delegate",
    "subagent_result",
    "final",
    "error",
]

# ---------- TraceStep ----------


class TraceStep(BaseModel):
    """单条追踪步骤，与 trace_step schema 一一对应。

    Attributes:
        index: 步骤序号（从 0 开始，自动递增）。
        kind:  步骤类型，枚举值见 ``StepKind``。
        payload: 任意附加数据。**禁止包含密钥等敏感信息。**
    """

    model_config = {"extra": "forbid"}

    index: int = Field(..., ge=0, description="步骤序号（≥ 0）")
    kind: StepKind = Field(..., description="步骤类型")
    payload: Optional[Dict[str, Any]] = Field(
        default=None, description="附加数据（禁止包含密钥）"
    )


# ---------- AssistantRunTrace ----------


class AssistantRunTrace(BaseModel):
    """一次 Agent 运行的完整追踪记录。

    Attributes:
        run_id: 本次运行的唯一标识（UUID）。
        parent_run_id: 父运行 ID（子代理场景下使用）。
        depth: 嵌套深度，根运行为 0。
        steps: 有序的追踪步骤列表。
    """

    model_config = {"extra": "forbid"}

    run_id: str = Field(..., min_length=1, description="运行唯一标识")
    parent_run_id: Optional[str] = Field(
        default=None, description="父运行 ID"
    )
    depth: int = Field(default=0, ge=0, description="嵌套深度")
    steps: List[TraceStep] = Field(default_factory=list, description="步骤列表")

    # ---- builder 方法 ----

    def add_step(
        self,
        kind: StepKind,
        payload: Optional[Dict[str, Any]] = None,
    ) -> TraceStep:
        """追加一条步骤并自动分配 index。"""
        step = TraceStep(index=len(self.steps), kind=kind, payload=payload)
        self.steps.append(step)
        return step

    def to_json(self, indent: int = 2) -> str:
        """序列化为 JSON 字符串（排除值为 None 的字段以匹配 schema）。"""
        return self.model_dump_json(indent=indent, exclude_none=True)

    def to_human_readable(self) -> str:
        """生成简洁的文本格式，用于 ``--trace human`` 输出。"""
        lines: list[str] = [
            f"Run: {self.run_id}  depth={self.depth}",
        ]
        if self.parent_run_id:
            lines[0] += f"  parent={self.parent_run_id}"

        for step in self.steps:
            prefix = f"  [{step.index}] {step.kind}"
            if step.payload:
                detail = ", ".join(
                    f"{k}={v!r}" for k, v in step.payload.items()
                )
                prefix += f"  {detail}"
            lines.append(prefix)

        return "\n".join(lines)


# ---------- 工厂函数 ----------


def new_trace(
    parent_run_id: Optional[str] = None,
    depth: int = 0,
    *,
    on_step: Optional[Callable[[TraceStep], None]] = None,
) -> AssistantRunTrace:
    """创建一条新的追踪记录，自动生成 UUID 作为 run_id。

    Parameters
    ----------
    on_step:
        每追加一条步骤后调用（与 OpenClaw 对齐的「流式过程」钩子）。
        回调内请勿抛错；如需记录失败由调用方自行 try/except。
    """
    trace = AssistantRunTrace(
        run_id=uuid.uuid4().hex,
        parent_run_id=parent_run_id,
        depth=depth,
    )
    if on_step is None:
        return trace

    _orig_add = trace.add_step

    def _wrapped_add(
        kind: StepKind,
        payload: Optional[Dict[str, Any]] = None,
    ) -> TraceStep:
        step = _orig_add(kind, payload)
        try:
            on_step(step)
        except Exception:
            logger.exception("trace on_step callback failed")
        return step

    trace.add_step = _wrapped_add  # type: ignore[method-assign]
    return trace
