"""
三国狼人杀 - 消息中心（模拟 AgentScope MsgHub / fanout_pipeline）

以消息驱动代替状态机：游戏流程被建模为「在特定上下文中，以何种模式进行消息交换」。
- MsgHub：建立临时通信频道（如仅狼人可见），支持广播公告与多轮讨论。
- fanout_pipeline：向多个智能体并行发送同一消息并收集结构化响应（如投票、击杀目标）。
"""

import asyncio
from typing import Any, List, Type, TypeVar

from pydantic import BaseModel

# 泛型：结构化输出模型类型
T = TypeVar("T", bound=BaseModel)


class MsgHub:
    """
    消息中心：为指定智能体列表建立通信上下文，支持广播与关闭广播后的点对点收集。
    对应 AgentScope 的 MsgHub(agents, enable_auto_broadcast=True, announcement=...)。
    """

    def __init__(
        self,
        agents: List[Any],
        *,
        enable_auto_broadcast: bool = True,
        announcement: str = "",
    ):
        self.agents = agents
        self._auto_broadcast = enable_auto_broadcast
        self._announcement = announcement
        self._history: List[str] = []

    async def __aenter__(self) -> "MsgHub":
        # 进入时若有公告则向所有智能体广播
        if self._announcement and self._auto_broadcast:
            for agent in self.agents:
                print(f"  [广播 -> {getattr(agent, 'name', agent)}] {self._announcement[:60]}...")
            self._history.append(self._announcement)
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    def set_auto_broadcast(self, value: bool) -> None:
        """关闭/开启自动广播（例如讨论结束后关闭，再进行投票收集）。"""
        self._auto_broadcast = value

    def add_to_history(self, text: str) -> None:
        """将一条消息加入当前频道历史，供后续智能体参考（可选）。"""
        self._history.append(text)


async def fanout_pipeline(
    agents: List[Any],
    msg: str,
    structured_model: Type[T],
    *,
    enable_gather: bool = True,
) -> List[T]:
    """
    向所有智能体并行发送同一条消息，并收集各自的结构化输出。
    对应 AgentScope 的 fanout_pipeline(agents, msg, structured_model=..., enable_gather=False)。
    用于投票、狼人击杀、预言家查验、女巫行动等「同时收集多份决策」的阶段。
    """
    async def call_one(agent: Any) -> T:
        try:
            return await agent.respond(msg, structured_model)
        except Exception as e:
            name = getattr(agent, "name", str(agent))
            print(f"⚠️ {name} 响应时出错: {e}")
            # 返回默认实例，确保游戏可继续（容错机制）
            return structured_model()

    tasks = [call_one(a) for a in agents]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    out: List[T] = []
    for r in results:
        if isinstance(r, Exception):
            # 容错：无法解析时返回默认实例（若模型有无参构造）
            try:
                out.append(structured_model())
            except Exception:
                out.append(r)  # 类型忽略，由上层处理
        else:
            out.append(r)
    return out
