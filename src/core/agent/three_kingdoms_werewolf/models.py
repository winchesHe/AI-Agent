"""
三国狼人杀 - 结构化输出数据模型

通过 Pydantic 定义各阶段智能体的输出格式，实现游戏规则的自动化约束。
对应 AgentScope 中「用结构化输出约束游戏规则」的设计：
- 女巫无法同时对同一目标使用解药和毒药（由字段与校验表达）
- 预言家每晚只能查验一名玩家（单目标字段）
- 投票/讨论阶段格式统一，便于消息中心收集与裁定
"""

from typing import Optional
from pydantic import BaseModel, Field


class DiscussionModelCN(BaseModel):
    """讨论阶段的输出格式（狼人讨论、白天发言等）。"""

    reach_agreement: bool = Field(
        description="是否已达成一致意见",
        default=False,
    )
    confidence_level: int = Field(
        description="对当前推理的信心程度(1-10)",
        ge=1,
        le=10,
        default=5,
    )
    key_evidence: Optional[str] = Field(
        description="支持你观点的关键证据",
        default=None,
    )


class WerewolfKillModelCN(BaseModel):
    """狼人击杀阶段的输出格式。"""

    target_name: str = Field(
        description="今晚要击杀的玩家姓名",
        default="",
    )


class WitchActionModelCN(BaseModel):
    """女巫行动的输出格式。"""

    use_antidote: bool = Field(description="是否使用解药", default=False)
    use_poison: bool = Field(description="是否使用毒药", default=False)
    target_name: Optional[str] = Field(
        description="毒药目标玩家姓名（仅在使用毒药时必填）",
        default=None,
    )


class SeerCheckModelCN(BaseModel):
    """预言家查验阶段的输出格式。"""

    target_name: str = Field(
        description="今晚要查验的玩家姓名",
        default="",
    )


def get_vote_model_cn(candidate_names: list[str]):
    """
    根据当前存活玩家列表动态生成投票模型类。
    保证投票目标只能是存活玩家之一，实现规则约束。
    """

    class VoteModelCN(BaseModel):
        """投票阶段的输出格式。"""

        vote_target: str = Field(
            description=f"你要投票淘汰的玩家姓名，必须从以下名单中选择一个：{candidate_names}",
            default="",
        )

    return VoteModelCN
