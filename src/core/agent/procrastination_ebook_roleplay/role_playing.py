"""
CAMEL RolePlaying 风格的「作家 + 心理学家」双智能体协作（OpenAI 兼容 API）。

不依赖 camel-ai 库：用同一套 HelloAgentsLLM 分别扮演两角色，对话拓扑与示例一致：
每轮先由作家根据上一轮心理学家发言提出需求，再由心理学家回应；循环直至任务完成标记或轮次上限。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from core.llm.llm_client import HelloAgentsLLM

from .prompts import (
    INIT_ASSISTANT_SEED,
    PSYCHOLOGIST_SYSTEM,
    TASK_DONE_TAG,
    TASK_PROMPT,
    WRITER_SYSTEM,
)


@dataclass
class SimpleMsg:
    """与示例中 role_play_session.*.msg 类似的最小消息载体。"""

    content: str


@dataclass
class TurnBundle:
    msg: SimpleMsg


class RolePlayingEbookSession:
    """
    对标 CAMEL RolePlaying(with_task_specify=False) 的简化实现。

    - init_chat(): 返回首轮 step 所需的「上一轮心理学家侧」输入；此处为种子开场白。
    - step(input_msg): 作家先根据 input_msg 发言，心理学家再回应作家；返回 (assistant, user)。
    """

    def __init__(
        self,
        llm: HelloAgentsLLM,
        task_prompt: str = TASK_PROMPT,
        assistant_role_name: str = "心理学家",
        user_role_name: str = "作家",
    ):
        self.llm = llm
        self.task_prompt = task_prompt.strip()
        self.assistant_role_name = assistant_role_name
        self.user_role_name = user_role_name
        # 与 CAMEL 示例一致：对外展示的「具体任务」可直接等于传入的 task_prompt
        self.task_prompt_display = self.task_prompt

    def init_chat(self) -> SimpleMsg:
        return SimpleMsg(content=INIT_ASSISTANT_SEED)

    def _append(self, history: List[dict], role: str, content: str) -> None:
        history.append({"role": role, "content": content})

    def _call_role(self, system: str, history: List[dict]) -> str:
        messages = [{"role": "system", "content": system}] + list(history)
        return (self.llm.think(messages, temperature=0.3, stream=False) or "").strip()

    def step(self, input_msg: SimpleMsg) -> Tuple[TurnBundle, TurnBundle]:
        """
        input_msg：上一轮心理学家的发言（首轮为 init_chat 的种子）。

        返回 (assistant_response, user_response)，与常见 CAMEL 教程中的解包顺序一致；
        打印时若希望先作家后心理学家，可先展示 user 再展示 assistant。
        """
        if not (input_msg and input_msg.content):
            empty = SimpleMsg(content="")
            return TurnBundle(empty), TurnBundle(empty)

        writer_history: List[dict] = [
            {
                "role": "user",
                "content": f"【全书任务说明】\n{self.task_prompt}\n\n"
                f"【上一轮心理学家发言】\n{input_msg.content}",
            }
        ]
        writer_content = self._call_role(WRITER_SYSTEM, writer_history)
        user_msg = SimpleMsg(content=writer_content)

        psych_history: List[dict] = [
            {
                "role": "user",
                "content": f"【全书任务说明】\n{self.task_prompt}\n\n"
                f"【作家本轮需求】\n{writer_content}",
            }
        ]
        psych_content = self._call_role(PSYCHOLOGIST_SYSTEM, psych_history)
        assistant_msg = SimpleMsg(content=psych_content)

        return TurnBundle(assistant_msg), TurnBundle(user_msg)


def run_procrastination_ebook_collab(
    llm: Optional[HelloAgentsLLM] = None,
    chat_turn_limit: int = 30,
) -> int:
    """
    驱动完整协作循环。返回实际执行的 step 轮次数。
    """
    llm = llm or HelloAgentsLLM()
    session = RolePlayingEbookSession(llm=llm)
    input_msg = session.init_chat()
    n = 0
    while n < chat_turn_limit:
        n += 1
        assistant_bundle, user_bundle = session.step(input_msg)
        a, u = assistant_bundle.msg, user_bundle.msg
        if not a.content or not u.content:
            break
        print(f"\n{'='*60}\n轮次 {n}\n{'='*60}")
        print(f"\n【{session.user_role_name} (AI User)】\n\n{u.content}\n")
        print(f"\n【{session.assistant_role_name} (AI Assistant)】\n\n{a.content}\n")
        if TASK_DONE_TAG in u.content or TASK_DONE_TAG in a.content:
            print(f"\n✅ 检测到 {TASK_DONE_TAG}，协作结束。")
            break
        input_msg = a
    print(f"\n共完成 {n} 轮 step。")
    return n
