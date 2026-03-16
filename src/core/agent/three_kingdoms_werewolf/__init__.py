# 三国狼人杀 Agent：基于消息驱动的多智能体协作示例
# 架构设计对齐 AgentScope 的消息驱动、MsgHub、结构化输出等理念

from .game import ThreeKingdomsWerewolfGame
from .agents import create_player_agent, create_moderator_agent
from .models import (
    DiscussionModelCN,
    WerewolfKillModelCN,
    WitchActionModelCN,
    SeerCheckModelCN,
)

__all__ = [
    "ThreeKingdomsWerewolfGame",
    "create_player_agent",
    "create_moderator_agent",
    "DiscussionModelCN",
    "WerewolfKillModelCN",
    "WitchActionModelCN",
    "SeerCheckModelCN",
]
