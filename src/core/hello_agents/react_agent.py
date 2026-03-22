"""ReActAgent：Thought / Action 循环，与 ToolRegistry 集成。"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple

from core.llm.llm_client import HelloAgentsLLM

from .agent import Agent

if TYPE_CHECKING:
    from core.runtime.trace import AssistantRunTrace
from .config import Config
from .message import Message
from .tool_registry import ToolRegistry

MY_REACT_PROMPT = """你是一个具备推理和行动能力的AI助手。你可以通过思考分析问题，然后调用合适的工具来获取信息，最终给出准确的答案。

## 可用工具
{tools}

## 工作流程
请严格按照以下格式进行回应，每次只能执行一个步骤:

Thought: 分析当前问题，思考需要什么信息或采取什么行动。
Action: 选择一个行动，格式必须是以下之一:
- `{{tool_name}}[{{tool_input}}]` - 调用指定工具
- `Finish[最终答案]` - 当你有足够信息给出最终答案时

## 重要提醒
1. 每次回应必须包含Thought和Action两部分
2. 工具调用的格式必须严格遵循:工具名[参数]
3. 只有当你确信有足够信息回答问题时，才使用Finish
4. 如果工具返回的信息不够，继续使用其他工具或相同工具的不同参数

## 当前任务
**Question:** {question}

## 执行历史
{history}

现在开始你的推理和行动:
"""


class ReActAgent(Agent):
    """推理与行动（ReAct）范式，单步 Thought+Action，直至 Finish 或达到步数上限。"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        tool_registry: ToolRegistry,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_steps: int = 5,
        custom_prompt: Optional[str] = None,
        verbose: bool = False,
    ) -> None:
        super().__init__(name, llm, system_prompt, config)
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.current_history: List[str] = []
        self.prompt_template = custom_prompt if custom_prompt else MY_REACT_PROMPT
        self.verbose = verbose

    def _complete_llm_turn(
        self,
        messages: List[dict],
        *,
        current_step: int,
        llm_stream_callback: Optional[Callable[[int, str, str], None]],
        **llm_kwargs: object,
    ) -> str:
        """单次 Chat 调用：可选流式，返回 assistant 全文（strip 后）。"""

        if llm_stream_callback is not None:
            llm_stream_callback(current_step, "", "step_start")
            parts: List[str] = []
            for piece in self.llm.stream_invoke(messages, **llm_kwargs):
                parts.append(piece)
                llm_stream_callback(current_step, "".join(parts), "delta")
            text = "".join(parts).strip()
            llm_stream_callback(current_step, text, "end")
            return text
        out = self.llm.invoke(messages, **llm_kwargs)
        return (out or "").strip()

    def run(
        self,
        input_text: str,
        *,
        trace: Optional["AssistantRunTrace"] = None,
        llm_stream_callback: Optional[Callable[[int, str, str], None]] = None,
        **kwargs: object,
    ) -> str:
        self.current_history = []
        current_step = 0
        if self.verbose:
            print(f"\n🤖 {self.name} 开始处理问题: {input_text}")

        while current_step < self.max_steps:
            current_step += 1
            if self.verbose:
                print(f"\n--- 第 {current_step} 步 ---")

            tools_desc = self.tool_registry.get_tools_description()
            history_str = "\n".join(self.current_history)
            prompt = self.prompt_template.format(
                tools=tools_desc,
                question=input_text,
                history=history_str,
            )

            messages = [{"role": "user", "content": prompt}]
            response_text = self._complete_llm_turn(
                messages,
                current_step=current_step,
                llm_stream_callback=llm_stream_callback,
                **kwargs,
            )

            _thought, action = self._parse_output(response_text)

            if trace is not None:
                trace.add_step(
                    "thought",
                    {
                        "step": current_step,
                        "thought": (_thought or "")[:2000],
                        "action_preview": (action or "")[:500],
                    },
                )

            if action and action.strip().startswith("Finish"):
                final_answer = self._parse_finish_payload(action)
                self.add_message(Message(content=input_text, role="user"))
                self.add_message(Message(content=final_answer, role="assistant"))
                return final_answer

            if action:
                tool_name, tool_input = self._parse_tool_action(action)
                if trace is not None:
                    call_kind = (
                        "mcp_call" if tool_name.startswith("mcp__") else "tool_call"
                    )
                    trace.add_step(
                        call_kind,
                        {
                            "step": current_step,
                            "tool_name": tool_name,
                            "tool_input_preview": (tool_input or "")[:800],
                        },
                    )
                observation = self.tool_registry.execute_tool(tool_name, tool_input)
                if trace is not None:
                    res_kind = (
                        "mcp_result" if tool_name.startswith("mcp__") else "tool_result"
                    )
                    trace.add_step(
                        res_kind,
                        {
                            "step": current_step,
                            "tool_name": tool_name,
                            "observation_preview": (observation or "")[:2000],
                        },
                    )
                self.current_history.append(f"Action: {action.strip()}")
                self.current_history.append(f"Observation: {observation}")

        final_answer = "抱歉，我无法在限定步数内完成这个任务。"
        self.add_message(Message(content=input_text, role="user"))
        self.add_message(Message(content=final_answer, role="assistant"))
        return final_answer

    def _parse_output(self, text: str) -> Tuple[str, str]:
        thought = ""
        for line in text.splitlines():
            s = line.strip()
            if s.lower().startswith("thought:"):
                thought = s.split(":", 1)[1].strip()
        # 必须捕获从「行首 Action:」到全文末尾，否则多行 Finish[...] 只会留下第一行，
        # 导致无闭合 ] 时 _parse_finish_payload 只得到前缀（例如「目前可用工具有：」）。
        m = re.search(r"(?im)^\s*Action:\s*(.*)\Z", text, re.DOTALL)
        action = m.group(1).strip() if m else ""
        if not action:
            m2 = re.search(
                r"Action:\s*(.+)",
                text,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if m2:
                action = m2.group(1).strip()
        return thought, action

    def _parse_tool_action(self, action: str) -> Tuple[str, str]:
        action = action.strip()
        if action.lower().startswith("finish"):
            return "", ""
        m = re.match(r"([^\[\]]+?)\[(.*)\]\s*$", action, re.DOTALL)
        if not m:
            return "error", f"无法解析 Action: {action}"
        tool_name = m.group(1).strip()
        tool_input = m.group(2).strip()
        return tool_name, tool_input

    def _parse_finish_payload(self, action: str) -> str:
        action = action.strip()
        low = action.lower()
        if not low.startswith("finish"):
            return action
        idx = action.find("[")
        if idx < 0:
            return action
        end = action.rfind("]")
        if end <= idx:
            return action[idx + 1 :].strip()
        return action[idx + 1 : end].strip()
