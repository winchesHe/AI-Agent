"""SimpleAgent：基础对话范式，可选基于标记的工具调用与流式输出。"""
from __future__ import annotations

import re
from typing import Iterator, Optional

from core.llm.llm_client import HelloAgentsLLM

from .agent import Agent
from .config import Config
from .message import Message
from .tool_registry import ToolRegistry


class SimpleAgent(Agent):
    """最简对话智能体；可挂载 ToolRegistry，通过 `[TOOL_CALL:name:args]` 触发工具。"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        tool_registry: Optional[ToolRegistry] = None,
        enable_tool_calling: bool = True,
    ) -> None:
        super().__init__(name, llm, system_prompt, config)
        self.tool_registry = tool_registry
        self.enable_tool_calling = bool(
            enable_tool_calling and tool_registry is not None
        )

    def run(
        self, input_text: str, max_tool_iterations: int = 3, **kwargs: object
    ) -> str:
        messages: list[dict[str, str]] = []
        enhanced_system_prompt = self._get_enhanced_system_prompt()
        messages.append({"role": "system", "content": enhanced_system_prompt})
        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": input_text})

        if not self.enable_tool_calling:
            response = self.llm.invoke(messages, **kwargs)
            self.add_message(Message(content=input_text, role="user"))
            self.add_message(Message(content=response, role="assistant"))
            return response

        return self._run_with_tools(
            messages, input_text, max_tool_iterations, **kwargs
        )

    def _get_enhanced_system_prompt(self) -> str:
        base_prompt = self.system_prompt or "你是一个有用的AI助手。"

        if not self.enable_tool_calling or not self.tool_registry:
            return base_prompt

        tools_description = self.tool_registry.get_tools_description()
        if not tools_description or tools_description == "暂无可用工具":
            return base_prompt

        tools_section = "\n\n## 可用工具\n"
        tools_section += "你可以使用以下工具来帮助回答问题:\n"
        tools_section += tools_description + "\n"

        tools_section += "\n## 工具调用格式\n"
        tools_section += "当需要使用工具时，请使用以下格式:\n"
        tools_section += "`[TOOL_CALL:{tool_name}:{parameters}]`\n"
        tools_section += (
            "例如:`[TOOL_CALL:search:Python编程]` 或 "
            "`[TOOL_CALL:memory:recall=用户信息]`\n\n"
        )
        tools_section += "工具调用结果会自动插入到对话中，然后你可以基于结果继续回答。\n"

        return base_prompt + tools_section

    def _run_with_tools(
        self,
        messages: list[dict[str, str]],
        input_text: str,
        max_tool_iterations: int,
        **kwargs: object,
    ) -> str:
        current_iteration = 0
        final_response = ""

        while current_iteration < max_tool_iterations:
            response = self.llm.invoke(messages, **kwargs)
            tool_calls = self._parse_tool_calls(response)

            if tool_calls:
                tool_results: list[str] = []
                clean_response = response

                for call in tool_calls:
                    result = self._execute_tool_call(
                        call["tool_name"], call["parameters"]
                    )
                    tool_results.append(result)
                    clean_response = clean_response.replace(call["original"], "")

                messages.append({"role": "assistant", "content": clean_response})
                tool_results_text = "\n\n".join(tool_results)
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"工具执行结果:\n{tool_results_text}\n\n"
                            "请基于这些结果给出完整的回答。"
                        ),
                    }
                )
                current_iteration += 1
                continue

            final_response = response
            break

        if current_iteration >= max_tool_iterations and not final_response:
            final_response = self.llm.invoke(messages, **kwargs)

        self.add_message(Message(content=input_text, role="user"))
        self.add_message(Message(content=final_response, role="assistant"))
        return final_response

    def _parse_tool_calls(self, text: str) -> list[dict[str, str]]:
        pattern = r"\[TOOL_CALL:([^:]+):([^\]]+)\]"
        matches = re.findall(pattern, text)

        tool_calls: list[dict[str, str]] = []
        for tool_name, parameters in matches:
            tool_calls.append(
                {
                    "tool_name": tool_name.strip(),
                    "parameters": parameters.strip(),
                    "original": f"[TOOL_CALL:{tool_name}:{parameters}]",
                }
            )

        return tool_calls

    def _execute_tool_call(self, tool_name: str, parameters: str) -> str:
        if not self.tool_registry:
            return "❌ 错误:未配置工具注册表"

        try:
            if tool_name == "calculator":
                result = self.tool_registry.execute_tool(tool_name, parameters)
            else:
                param_dict = self._parse_tool_parameters(tool_name, parameters)
                tool = self.tool_registry.get_tool(tool_name)
                if not tool:
                    return f"❌ 错误:未找到工具 '{tool_name}'"
                result = tool.run(param_dict)

            return f"🔧 工具 {tool_name} 执行结果:\n{result}"

        except Exception as e:
            return f"❌ 工具调用失败:{str(e)}"

    def _parse_tool_parameters(self, tool_name: str, parameters: str) -> dict[str, str]:
        param_dict: dict[str, str] = {}

        if "=" in parameters:
            if "," in parameters:
                pairs = parameters.split(",")
                for pair in pairs:
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        param_dict[key.strip()] = value.strip()
            else:
                key, value = parameters.split("=", 1)
                param_dict[key.strip()] = value.strip()
        else:
            if tool_name == "search":
                param_dict = {"query": parameters}
            elif tool_name == "memory":
                param_dict = {"action": "search", "query": parameters}
            else:
                param_dict = {"input": parameters}

        return param_dict

    def stream_run(self, input_text: str, **kwargs: object) -> Iterator[str]:
        messages: list[dict[str, str]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": input_text})

        full_response = ""
        for chunk in self.llm.stream_invoke(messages, **kwargs):
            full_response += chunk
            yield chunk

        self.add_message(Message(content=input_text, role="user"))
        self.add_message(Message(content=full_response, role="assistant"))

    def add_tool(self, tool: object) -> None:
        if self.tool_registry is None:
            self.tool_registry = ToolRegistry()
            self.enable_tool_calling = True

        register = getattr(self.tool_registry, "register_tool", None)
        if register is not None:
            register(tool)

    def has_tools(self) -> bool:
        return self.enable_tool_calling and self.tool_registry is not None

    def remove_tool(self, tool_name: str) -> bool:
        if self.tool_registry:
            self.tool_registry.unregister(tool_name)
            return True
        return False

    def list_tools(self) -> list[str]:
        if self.tool_registry:
            return self.tool_registry.list_tools()
        return []
