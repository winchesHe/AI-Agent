"""SubAgent 委派 —— 深度限制与工具白名单控制。

SubAgent 运行在同一进程内独立 LoopDriver 实例，
max_delegation_depth 默认 2，子 Run 独立预算
（迭代数上限为父的 1/2 向下取整）。
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from core.hello_agents.tool_registry import ToolRegistry
from core.llm.llm_client import HelloAgentsLLM

from .config import LoopConfig
from .loop_driver import LoopDriver, LoopResult
from .trace import AssistantRunTrace


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class DelegationError(Exception):
    """委派深度超限或校验失败时抛出。"""


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class SubAgentDefinition(BaseModel):
    """子代理定义。"""

    id: str = Field(description="子代理唯一标识")
    tool_allowlist: List[str] = Field(description="允许使用的工具名称列表")
    max_iterations: int = Field(default=5, ge=1, description="迭代预算上限")
    can_delegate: bool = Field(default=False, description="是否允许进一步委派")


class SubAgentResult(BaseModel):
    """子代理运行结果。"""

    agent_id: str = Field(description="子代理标识")
    answer: str = Field(description="最终回答文本")
    trace: AssistantRunTrace = Field(description="本次运行的追踪记录")
    success: bool = Field(description="是否正常完成")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class SubAgentRunner:
    """管理子代理委派，强制深度限制与工具白名单。

    Parameters
    ----------
    llm:
        LLM 客户端实例。
    full_registry:
        完整的工具注册表，子代理仅获得其允许的子集。
    max_delegation_depth:
        最大委派嵌套深度，默认 2。
    """

    DELEGATION_TOOL_NAMES = frozenset({"delegate", "sub_agent", "subagent"})

    def __init__(
        self,
        llm: HelloAgentsLLM,
        full_registry: ToolRegistry,
        max_delegation_depth: int = 2,
    ) -> None:
        self.llm = llm
        self.full_registry = full_registry
        self.max_delegation_depth = max_delegation_depth

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def delegate(
        self,
        definition: SubAgentDefinition,
        task: str,
        parent_run_id: str,
        depth: int,
    ) -> SubAgentResult:
        """委派任务给子代理并返回结构化结果。

        Parameters
        ----------
        definition:
            子代理定义（工具白名单、迭代预算等）。
        task:
            交给子代理执行的任务描述。
        parent_run_id:
            父运行 ID，用于追踪关联。
        depth:
            当前委派深度（根运行为 0）。

        Raises
        ------
        DelegationError
            当 *depth* 已达 ``max_delegation_depth``，或工具白名单
            包含注册表中不存在的工具时抛出。
        """
        if depth >= self.max_delegation_depth:
            raise DelegationError(
                f"Delegation depth {depth} reached limit "
                f"{self.max_delegation_depth}"
            )

        filtered_registry = self._build_filtered_registry(definition)

        loop_config = LoopConfig(
            max_iterations=definition.max_iterations,
        )

        driver = LoopDriver(
            llm=self.llm,
            tool_registry=filtered_registry,
            loop_config=loop_config,
            parent_run_id=parent_run_id,
            depth=depth + 1,
        )

        result: LoopResult = driver.run(task)

        return SubAgentResult(
            agent_id=definition.id,
            answer=result.answer,
            trace=result.trace,
            success=result.success,
        )

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _build_filtered_registry(
        self,
        definition: SubAgentDefinition,
    ) -> ToolRegistry:
        """根据白名单从完整注册表中筛选工具，返回新的 ToolRegistry。"""
        available = set(self.full_registry.list_tools())
        missing = set(definition.tool_allowlist) - available
        if missing:
            raise DelegationError(
                f"Tools not found in registry: {sorted(missing)}"
            )

        filtered = ToolRegistry()
        for name in definition.tool_allowlist:
            # 如果 can_delegate 为 False，跳过委派相关工具
            if not definition.can_delegate and name in self.DELEGATION_TOOL_NAMES:
                continue
            tool = self.full_registry.get_tool(name)
            if tool is not None:
                filtered.register_tool(tool)

        return filtered
