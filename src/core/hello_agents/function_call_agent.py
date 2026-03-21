"""FunctionCallAgent：基于 OpenAI Chat Completions 原生 tools / tool_calls 的循环。"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union, cast

from core.llm.llm_client import HelloAgentsLLM

from .agent import Agent
from .config import Config
from .message import Message
from .tool_registry import ToolRegistry


class FunctionCallAgent(Agent):
    """使用 OpenAI 函数调用协议；需底层 `HelloAgentsLLM.client` 为 OpenAI SDK 客户端。"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        tool_registry: ToolRegistry,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_iterations: int = 8,
    ) -> None:
        super().__init__(name, llm, system_prompt, config)
        self.tool_registry = tool_registry
        self.max_iterations = max_iterations

    def run(self, input_text: str, **kwargs: object) -> str:
        tools = self._build_tool_schemas()
        messages: List[Dict[str, Any]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": input_text})

        final_text = ""
        for _ in range(self.max_iterations):
            completion = self._invoke_with_tools(
                messages,
                tools,
                tool_choice=cast(Any, kwargs.get("tool_choice", "auto")),
                **kwargs,
            )
            choice = completion.choices[0]
            msg = choice.message
            assistant_content = self._extract_message_content(msg)

            tool_calls = getattr(msg, "tool_calls", None) or []
            if tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": assistant_content or None,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments or "{}",
                                },
                            }
                            for tc in tool_calls
                        ],
                    }
                )
                for tc in tool_calls:
                    name = tc.function.name
                    raw_args = tc.function.arguments or "{}"
                    args = self._parse_function_call_arguments(raw_args)
                    args = self._convert_parameter_types(name, args)
                    tool = self.tool_registry.get_tool(name)
                    if tool is None:
                        result = f"未知工具: {name}"
                    else:
                        result = tool.run(args)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result,
                        }
                    )
                continue

            final_text = (assistant_content or "").strip()
            break

        self.add_message(Message(content=input_text, role="user"))
        self.add_message(Message(content=final_text, role="assistant"))
        return final_text

    def _build_tool_schemas(self) -> List[Dict[str, Any]]:
        return self.tool_registry.openai_tools_payload()

    def _extract_message_content(self, message: Any) -> str:
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
                else:
                    parts.append(str(block))
            return "".join(parts)
        return str(content or "")

    def _parse_function_call_arguments(self, raw: str) -> Dict[str, Any]:
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _convert_parameter_types(
        self, _tool_name: str, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """占位：可按工具名把字符串转为数值等；当前原样返回。"""
        return dict(args)

    def _invoke_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_choice: Union[str, dict[str, Any]],
        **kwargs: object,
    ) -> Any:
        client = getattr(self.llm, "client", None) or getattr(
            self.llm, "_client", None
        )
        if client is None:
            raise RuntimeError(
                "HelloAgentsLLM 未正确初始化客户端，无法执行函数调用。"
            )

        create_kwargs: Dict[str, Any] = {
            "model": self.llm.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": tool_choice,
            "temperature": kwargs.get("temperature", self.llm.temperature),
        }
        mt = kwargs.get("max_tokens", self.llm.max_tokens)
        if mt is not None:
            create_kwargs["max_tokens"] = mt

        for k in ("top_p", "frequency_penalty", "presence_penalty", "seed"):
            if k in kwargs and kwargs[k] is not None:
                create_kwargs[k] = kwargs[k]

        return client.chat.completions.create(**create_kwargs)
