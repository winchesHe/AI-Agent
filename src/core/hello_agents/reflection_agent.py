"""ReflectionAgent：生成—反思—改进的多轮文本优化范式。"""
from __future__ import annotations

import re
from typing import Dict, Optional

from core.llm.llm_client import HelloAgentsLLM

from .agent import Agent
from .config import Config
from .message import Message

DEFAULT_PROMPTS: Dict[str, str] = {
    "initial": """
请根据以下要求完成任务:

任务: {task}

请提供一个完整、准确的回答。
""",
    "reflect": """
请仔细审查以下回答，并找出可能的问题或改进空间:

# 原始任务:
{task}

# 当前回答:
{content}

请分析这个回答的质量，指出不足之处，并提出具体的改进建议。
如果回答已经很好，请回答"无需改进"。
""",
    "refine": """
请根据反馈意见改进你的回答:

# 原始任务:
{task}

# 上一轮回答:
{last_attempt}

# 反馈意见:
{feedback}

请提供一个改进后的回答。
""",
}


def _format_prompt_template(template: str, **kwargs: str) -> str:
    """按模板中出现的占位符填充；未提供的键用空字符串，避免 KeyError。"""
    names = set(re.findall(r"\{(\w+)\}", template))
    data = {k: str(kwargs.get(k, "") or "") for k in names}
    return template.format(**data)


class ReflectionAgent(Agent):
    """通用反思智能体；可通过 custom_prompts 覆盖 initial / reflect / refine。"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_rounds: int = 3,
        custom_prompts: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(name, llm, system_prompt, config)
        self.max_rounds = max_rounds
        merged = dict(DEFAULT_PROMPTS)
        if custom_prompts:
            merged.update(custom_prompts)
        self.prompts = merged

    def run(self, input_text: str, **kwargs: object) -> str:
        task = input_text
        messages_i = [
            {
                "role": "user",
                "content": _format_prompt_template(self.prompts["initial"], task=task),
            }
        ]
        if self.system_prompt:
            messages_i.insert(
                0, {"role": "system", "content": self.system_prompt}
            )
        content = self.llm.invoke(messages_i, **kwargs)

        for _ in range(self.max_rounds):
            reflect_msg = _format_prompt_template(
                self.prompts["reflect"], task=task, content=content
            )
            reflect_messages = [{"role": "user", "content": reflect_msg}]
            if self.system_prompt:
                reflect_messages.insert(
                    0, {"role": "system", "content": self.system_prompt}
                )
            feedback = self.llm.invoke(reflect_messages, **kwargs).strip()
            if "无需改进" in feedback:
                break

            refine_msg = _format_prompt_template(
                self.prompts["refine"],
                task=task,
                last_attempt=content,
                feedback=feedback,
            )
            refine_messages = [{"role": "user", "content": refine_msg}]
            if self.system_prompt:
                refine_messages.insert(
                    0, {"role": "system", "content": self.system_prompt}
                )
            content = self.llm.invoke(refine_messages, **kwargs)

        self.add_message(Message(content=input_text, role="user"))
        self.add_message(Message(content=content, role="assistant"))
        return content
