"""
三国狼人杀 - 角色提示词与主持人话术

实现「角色建模的双重挑战」：同时注入游戏功能角色（狼人、预言家等）与三国人格角色
（刘备、曹操等），使智能体在遵守规则的前提下体现人物性格。
"""
from typing import Optional

# 三国人物与游戏角色的默认映射（姓名 -> 可选的性格简述，用于提示词）
THREE_KINGDOMS_CHARACTERS = [
    "刘备",
    "关羽",
    "张飞",
    "诸葛亮",
    "曹操",
    "孙权",
    "周瑜",
    "司马懿",
]


def get_role_prompt(role: str, character: str) -> str:
    """
    获取角色提示词：融合游戏规则与人物性格。
    让智能体同时扮演好「游戏功能角色」和「文化人格角色」。
    """
    base_prompt = f"""你是{character}，在这场三国狼人杀游戏中扮演{role}。

重要规则：
1. 你只能通过对话和推理参与游戏
2. 不要尝试调用任何外部工具或函数
3. 严格按照要求的JSON格式回复

角色特点：
"""

    if role == "狼人":
        return (
            base_prompt
            + f"""
- 你是狼人阵营，目标是消灭所有好人
- 夜晚可以与其他狼人协商击杀目标
- 白天要隐藏身份，误导好人
- 以{character}的性格说话和行动
"""
        )
    if role == "预言家":
        return (
            base_prompt
            + f"""
- 你是好人阵营，每晚可以查验一名玩家的真实身份（好人/狼人）
- 白天可根据查验结果引导大家投票，但需注意不要暴露太早
- 以{character}的性格说话和行动
"""
        )
    if role == "女巫":
        return (
            base_prompt
            + f"""
- 你是好人阵营，拥有一瓶解药和一瓶毒药（各只能用一次）
- 解药可救活当晚被狼人击杀的玩家，毒药可毒杀一名玩家
- 不能对同一晚同时使用解药和毒药
- 以{character}的性格说话和行动
"""
        )
    # 村民
    return (
        base_prompt
        + f"""
- 你是好人阵营的村民，没有特殊技能
- 通过白天发言和投票找出狼人
- 以{character}的性格说话和行动
"""
    )


def format_player_list(players: list) -> str:
    """将玩家列表格式化为可读字符串，用于主持人公告。"""
    return "、".join(getattr(p, "name", str(p)) for p in players)


def moderator_announce_night(round_num: int) -> str:
    """主持人：夜幕降临公告。"""
    return f"======== 第 {round_num} 晚 ======== 夜幕降临，请闭眼。"


def moderator_announce_werewolf_discuss(alive_names: str) -> str:
    """主持人：狼人讨论阶段公告。"""
    return f"狼人们，请讨论今晚的击杀目标。存活玩家：{alive_names}"


def moderator_announce_werewolf_kill() -> str:
    """主持人：狼人请选择击杀目标。"""
    return "请选择击杀目标（回复 JSON：{\"target_name\": \"玩家名\"}）"


def moderator_announce_seer_check(alive_names: str) -> str:
    """主持人：预言家请查验。"""
    return f"预言家，请选择要查验的玩家。存活玩家：{alive_names}"


def moderator_announce_witch(
    killed_name: Optional[str], alive_names: str
) -> str:
    """主持人：女巫行动（告知是否有人被击杀、存活名单）。"""
    if killed_name:
        return (
            f"女巫，今晚被击杀的是 {killed_name}。存活玩家：{alive_names}。"
            "你是否使用解药？是否使用毒药？若用毒请指定目标。"
            "回复 JSON：{\"use_antidote\": true/false, \"use_poison\": true/false, \"target_name\": \"玩家名或null\"}"
        )
    return (
        f"女巫，今晚无人被击杀。存活玩家：{alive_names}。"
        "你是否使用毒药？若用毒请指定目标。"
        "回复 JSON：{\"use_antidote\": false, \"use_poison\": true/false, \"target_name\": \"玩家名或null\"}"
    )


def moderator_announce_day_result(round_num: int, night_events: str) -> str:
    """主持人：天亮，公布昨夜结果。"""
    return f"======== 第 {round_num} 天 ======== 天亮了。{night_events}"


def moderator_announce_day_discuss(alive_names: str) -> str:
    """主持人：白天讨论。"""
    return f"请各位存活玩家依次发言讨论。存活玩家：{alive_names}"


def moderator_announce_vote(alive_names: str) -> str:
    """主持人：投票淘汰。"""
    return f"请投票选择要淘汰的玩家。存活玩家：{alive_names}"
