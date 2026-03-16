"""
三国狼人杀 - 游戏控制层 (Game Control Layer)

ThreeKingdomsWerewolfGame 作为主控制器，负责：
- 维护全局状态（存活/死亡、当前回合、角色身份）
- 推进游戏流程（夜晚：狼人→预言家→女巫；白天：讨论→投票）
- 裁定胜负（狼人全灭或狼人≥好人则结束）
- 通过消息中心（MsgHub / fanout_pipeline）驱动智能体交互，而非状态机
"""

import asyncio
import random
from collections import Counter
from typing import Any, List, Optional, Tuple

from .agents import PlayerAgent, create_moderator_agent, create_player_agent
from .msg_hub import MsgHub, fanout_pipeline
from .models import (
    DiscussionModelCN,
    SeerCheckModelCN,
    WerewolfKillModelCN,
    WitchActionModelCN,
    get_vote_model_cn,
)
from .prompts import (
    format_player_list,
    moderator_announce_day_discuss,
    moderator_announce_day_result,
    moderator_announce_night,
    moderator_announce_seer_check,
    moderator_announce_vote,
    moderator_announce_werewolf_discuss,
    moderator_announce_werewolf_kill,
    moderator_announce_witch,
    THREE_KINGDOMS_CHARACTERS,
)

# 狼人讨论最大轮数（每轮各狼发言一次）
MAX_DISCUSSION_ROUND = 2


class ThreeKingdomsWerewolfGame:
    """
    三国狼人杀游戏主控制器。
    架构上对应「游戏控制层」，依赖「智能体交互层」（MsgHub）和「角色建模层」（PlayerAgent）。
    """

    def __init__(
        self,
        llm_client: Any,
        *,
        characters: Optional[List[str]] = None,
        num_werewolves: int = 1,
        num_seers: int = 1,
        num_witches: int = 1,
        num_villagers: int = 1,
    ):
        """
        :param llm_client: 供所有玩家智能体调用的 LLM 客户端（如 HelloAgentsLLM）
        :param characters: 三国人物名列表，长度需 >= num_werewolves+num_seers+num_witches+num_villagers
        :param num_werewolves: 狼人数量
        :param num_seers: 预言家数量
        :param num_witches: 女巫数量
        :param num_villagers: 村民数量
        """
        self.llm_client = llm_client
        self.characters = characters or THREE_KINGDOMS_CHARACTERS[:4]
        roles: List[str] = []
        roles.extend(["狼人"] * num_werewolves)
        roles.extend(["预言家"] * num_seers)
        roles.extend(["女巫"] * num_witches)
        roles.extend(["村民"] * num_villagers)
        random.shuffle(roles)
        # 按角色创建玩家，姓名使用三国人物
        self.all_players: List[PlayerAgent] = []
        for i, (char, role) in enumerate(zip(self.characters, roles)):
            agent = create_player_agent(char, role, char, llm_client)
            self.all_players.append(agent)
        self.alive_players: List[PlayerAgent] = list(self.all_players)
        self.moderator = create_moderator_agent()
        # 角色索引，便于按身份筛选
        self.werewolves = [p for p in self.all_players if p.role == "狼人"]
        self.seer = next((p for p in self.all_players if p.role == "预言家"), None)
        self.witch = next((p for p in self.all_players if p.role == "女巫"), None)
        self.round_num = 0
        # 女巫技能使用状态
        self.witch_antidote_used = False
        self.witch_poison_used = False

    def _alive_names(self) -> str:
        """当前存活玩家姓名列表，用于公告。"""
        return format_player_list(self.alive_players)

    def _remove_from_alive(self, player: PlayerAgent) -> None:
        """将玩家移出存活列表（击杀/毒杀/投票出局）。"""
        if player in self.alive_players:
            self.alive_players.remove(player)

    def _check_win(self) -> Optional[str]:
        """
        胜负判定：狼人全灭 -> 好人胜；狼人数量 >= 好人数量 -> 狼人胜。
        :return: "good" | "werewolf" | None（未结束）
        """
        alive_wolves = [p for p in self.alive_players if p in self.werewolves]
        alive_good = len(self.alive_players) - len(alive_wolves)
        if not alive_wolves:
            return "good"
        if len(alive_wolves) >= alive_good:
            return "werewolf"
        return None

    async def werewolf_phase(self, round_num: int) -> Optional[PlayerAgent]:
        """
        狼人阶段：展示消息驱动的协作模式。
        通过 MsgHub 建立仅狼人可见的通信频道，先讨论再投票击杀目标。
        """
        if not self.werewolves:
            return None
        alive_names = self._alive_names()
        announcement = await self.moderator.announce(
            moderator_announce_werewolf_discuss(alive_names)
        )
        async with MsgHub(
            self.werewolves,
            enable_auto_broadcast=True,
            announcement=announcement,
        ) as werewolves_hub:
            # 讨论阶段：狼人依次发言交换策略（结构化讨论输出）
            for _ in range(MAX_DISCUSSION_ROUND):
                for wolf in self.werewolves:
                    if wolf not in self.alive_players:
                        continue
                    try:
                        await wolf.respond(
                            "请分析当前局势并表达你的观点。",
                            structured_model=DiscussionModelCN,
                        )
                    except Exception as e:
                        print(f"⚠️ {wolf.name} 讨论时出错: {e}")
            # 投票阶段：关闭广播，并行收集每位狼人的击杀决策
            werewolves_hub.set_auto_broadcast(False)
        kill_votes = await fanout_pipeline(
            [w for w in self.werewolves if w in self.alive_players],
            msg=await self.moderator.announce(moderator_announce_werewolf_kill()),
            structured_model=WerewolfKillModelCN,
            enable_gather=False,
        )
        # 统计票数，取最高票目标（若平票可随机或取第一个）
        names = [v.target_name.strip() for v in kill_votes if v.target_name.strip()]
        if not names:
            return None
        counter = Counter(names)
        target_name = counter.most_common(1)[0][0]
        target = next(
            (p for p in self.alive_players if p.name == target_name),
            None,
        )
        return target

    async def seer_phase(self, round_num: int) -> None:
        """预言家阶段：预言家选择一名玩家查验（仅逻辑记录，不公开）。"""
        if not self.seer or self.seer not in self.alive_players:
            return
        msg = await self.moderator.announce(
            moderator_announce_seer_check(self._alive_names())
        )
        try:
            result = await self.seer.respond(msg, structured_model=SeerCheckModelCN)
            target = next(
                (p for p in self.alive_players if p.name == result.target_name),
                None,
            )
            if target:
                identity = "狼人" if target in self.werewolves else "好人"
                print(f"  [预言家查验] {target.name} 是 {identity}")
        except Exception as e:
            print(f"⚠️ 预言家查验时出错: {e}")

    async def witch_phase(
        self,
        round_num: int,
        killed_by_wolves: Optional[PlayerAgent],
    ) -> Tuple[Optional[PlayerAgent], Optional[PlayerAgent]]:
        """
        女巫阶段：根据狼人击杀结果，女巫可选择使用解药/毒药。
        :return: (狼人击杀的最终结果，若用解药则为 None；毒杀目标，若有)
        """
        if not self.witch or self.witch not in self.alive_players:
            return (killed_by_wolves, None)
        killed_name = killed_by_wolves.name if killed_by_wolves else None
        msg = await self.moderator.announce(
            moderator_announce_witch(killed_name, self._alive_names())
        )
        try:
            action = await self.witch.respond(msg, structured_model=WitchActionModelCN)
        except Exception as e:
            print(f"⚠️ 女巫行动时出错: {e}")
            return (killed_by_wolves, None)
        # 解药：救活当晚被狼杀的人（若尚未使用解药），则白天不再结算该击杀
        if action.use_antidote and not self.witch_antidote_used and killed_by_wolves:
            self.witch_antidote_used = True
            print(f"  [女巫] 使用解药救活 {killed_by_wolves.name}")
            killed_by_wolves = None
        poison_target = None
        if action.use_poison and not self.witch_poison_used and action.target_name:
            self.witch_poison_used = True
            poison_target = next(
                (p for p in self.alive_players if p.name == action.target_name),
                None,
            )
            if poison_target:
                print(f"  [女巫] 使用毒药毒杀 {poison_target.name}")
        return (killed_by_wolves, poison_target)

    async def day_phase(
        self,
        round_num: int,
        killed_by_wolves: Optional[PlayerAgent],
        killed_by_witch: Optional[PlayerAgent],
    ) -> None:
        """
        白天阶段：公布昨夜结果，讨论后投票淘汰一人。
        """
        # 结算昨夜死亡（狼杀 + 女巫毒）
        night_events_parts = []
        if killed_by_wolves and killed_by_wolves in self.alive_players:
            self._remove_from_alive(killed_by_wolves)
            night_events_parts.append(f"{killed_by_wolves.name} 被狼人击杀。")
        if killed_by_witch and killed_by_witch in self.alive_players:
            self._remove_from_alive(killed_by_witch)
            night_events_parts.append(f"{killed_by_witch.name} 被女巫毒杀。")
        if not night_events_parts:
            night_events_parts.append("昨夜平安。")
        night_events = " ".join(night_events_parts)
        print(await self.moderator.announce(moderator_announce_day_result(round_num, night_events)))
        winner = self._check_win()
        if winner:
            return
        # 白天讨论（简化：一轮发言）
        discuss_msg = await self.moderator.announce(
            moderator_announce_day_discuss(self._alive_names())
        )
        for p in self.alive_players:
            try:
                await p.respond(discuss_msg, structured_model=DiscussionModelCN)
            except Exception as e:
                print(f"⚠️ {p.name} 讨论时出错: {e}")
        # 投票淘汰
        VoteModel = get_vote_model_cn([p.name for p in self.alive_players])
        vote_msg = await self.moderator.announce(moderator_announce_vote(self._alive_names()))
        vote_results = await fanout_pipeline(
            self.alive_players,
            vote_msg,
            VoteModel,
            enable_gather=False,
        )
        names = [v.vote_target.strip() for v in vote_results if v.vote_target.strip()]
        if not names:
            return
        counter = Counter(names)
        eliminate_name = counter.most_common(1)[0][0]
        eliminate = next(
            (p for p in self.alive_players if p.name == eliminate_name),
            None,
        )
        if eliminate:
            self._remove_from_alive(eliminate)
            print(f"  [投票出局] {eliminate.name}")

    async def run_async(self) -> str:
        """
        主流程：循环执行夜晚（狼人→预言家→女巫）与白天（公布→讨论→投票），直到一方获胜。
        :return: "good" | "werewolf"
        """
        print("======== 三国狼人杀 开始 ========")
        print("存活玩家:", self._alive_names())
        while True:
            self.round_num += 1
            # 夜晚
            print(await self.moderator.announce(moderator_announce_night(self.round_num)))
            killed_by_wolves = await self.werewolf_phase(self.round_num)
            await self.seer_phase(self.round_num)
            killed_by_wolves_final, killed_by_witch = await self.witch_phase(
                self.round_num, killed_by_wolves
            )
            # 白天（狼人击杀以女巫结算后的结果为准，解药救活则不再计入死亡）
            await self.day_phase(
                self.round_num,
                killed_by_wolves_final,
                killed_by_witch,
            )
            winner = self._check_win()
            if winner == "good":
                print("======== 好人阵营胜利 ========")
                return "good"
            if winner == "werewolf":
                print("======== 狼人阵营胜利 ========")
                return "werewolf"

    def run(self) -> str:
        """同步入口：在脚本中直接调用 run() 时使用。"""
        return asyncio.run(self.run_async())
