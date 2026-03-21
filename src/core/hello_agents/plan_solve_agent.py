"""PlanAndSolveAgent：先产出步骤列表，再逐步执行。"""
from __future__ import annotations

import ast
import re
from typing import List, Optional

from core.llm.llm_client import HelloAgentsLLM

from .agent import Agent
from .config import Config
from .message import Message

DEFAULT_PLANNER_PROMPT = """
你是一个顶级的AI规划专家。你的任务是将用户提出的复杂问题分解成一个由多个简单步骤组成的行动计划。
请确保计划中的每个步骤都是一个独立的、可执行的子任务，并且严格按照逻辑顺序排列。
你的输出必须是一个Python列表，其中每个元素都是一个描述子任务的字符串。

问题: {question}

请严格按照以下格式输出你的计划:
```python
["步骤1", "步骤2", "步骤3", ...]
```
"""

DEFAULT_EXECUTOR_PROMPT = """
你是一位顶级的AI执行专家。你的任务是严格按照给定的计划，一步步地解决问题。
你将收到原始问题、完整的计划、以及到目前为止已经完成的步骤和结果。
请你专注于解决"当前步骤"，并仅输出该步骤的最终答案，不要输出任何额外的解释或对话。

# 原始问题:
{question}

# 完整计划:
{plan}

# 历史步骤与结果:
{history}

# 当前步骤:
{current_step}

请仅输出针对"当前步骤"的回答:
"""


class PlanAndSolveAgent(Agent):
    """规划—执行范式；Planner 必须输出可解析的 Python 字符串列表。"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        custom_prompts: Optional[dict[str, str]] = None,
    ) -> None:
        super().__init__(name, llm, system_prompt, config)
        cp = custom_prompts or {}
        self.planner_prompt = cp.get("planner", DEFAULT_PLANNER_PROMPT)
        self.executor_prompt = cp.get("executor", DEFAULT_EXECUTOR_PROMPT)

    def run(self, input_text: str, **kwargs: object) -> str:
        question = input_text
        plan_raw = self._call_planner(question, **kwargs)
        plan_list = self._parse_plan_list(plan_raw)
        if not plan_list:
            msg = "无法从模型输出中解析有效计划列表。"
            self.add_message(Message(content=question, role="user"))
            self.add_message(Message(content=msg, role="assistant"))
            return msg

        history_lines: List[str] = []
        last_result = ""
        plan_display = "\n".join(f"{i+1}. {s}" for i, s in enumerate(plan_list))

        for step in plan_list:
            history_str = "\n".join(history_lines) if history_lines else "(无)"
            exec_user = self.executor_prompt.format(
                question=question,
                plan=plan_display,
                history=history_str,
                current_step=step,
            )
            exec_messages = [{"role": "user", "content": exec_user}]
            if self.system_prompt:
                exec_messages.insert(
                    0, {"role": "system", "content": self.system_prompt}
                )
            last_result = self.llm.invoke(exec_messages, **kwargs).strip()
            history_lines.append(f"步骤: {step}\n结果: {last_result}")

        self.add_message(Message(content=question, role="user"))
        self.add_message(Message(content=last_result, role="assistant"))
        return last_result

    def _call_planner(self, question: str, **kwargs: object) -> str:
        user_content = self.planner_prompt.format(question=question)
        messages = [{"role": "user", "content": user_content}]
        if self.system_prompt:
            messages.insert(0, {"role": "system", "content": self.system_prompt})
        return self.llm.invoke(messages, **kwargs)

    def _parse_plan_list(self, text: str) -> List[str]:
        block = text
        m = re.search(r"```(?:python)?\s*(\[[\s\S]*?\])\s*```", text)
        if m:
            block = m.group(1)
        else:
            m2 = re.search(r"(\[[\s\S]*?\])", text)
            if m2:
                block = m2.group(1)
        try:
            value = ast.literal_eval(block.strip())
        except (SyntaxError, ValueError, TypeError):
            return []
        if isinstance(value, list) and all(isinstance(x, str) for x in value):
            return [str(x).strip() for x in value if str(x).strip()]
        return []
