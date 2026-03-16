"""
三国狼人杀 - 智能体封装（角色建模层）

每个玩家是一个「基于 DialogAgent 理念」的实例：通过系统提示词注入游戏角色 + 三国人格，
仅通过对话参与游戏，不调用外部工具。主持人（Moderator）负责发布阶段公告。
"""

import asyncio
import json
import re
from typing import Any, Type, TypeVar

from pydantic import BaseModel

from .prompts import get_role_prompt

T = TypeVar("T", bound=BaseModel)


class PlayerAgent:
    """
    玩家智能体：对应 AgentScope 的 DialogAgent。
    具备 name、游戏角色（role）、三国人格（character），通过 respond(msg, structured_model)
    在消息驱动流程中返回结构化输出。
    """

    def __init__(
        self,
        name: str,
        role: str,
        character: str,
        llm_client: Any,
    ):
        self.name = name
        self.role = role
        self.character = character
        self.llm_client = llm_client
        self._system_prompt = get_role_prompt(role, character)

    async def respond(self, msg: str, structured_model: Type[T]) -> T:
        """
        接收一条消息，调用 LLM 生成回复，并解析为指定的 Pydantic 模型。
        在异步上下文中通过 asyncio.to_thread 调用同步 LLM，避免阻塞事件循环。
        """
        # 约束输出格式：要求返回合法 JSON，便于解析为 structured_model
        schema_hint = structured_model.model_json_schema()
        format_instruction = (
            f"请仅回复一个合法的 JSON 对象，不要包含其他文字。"
            f"字段含义参考：{json.dumps(schema_hint.get('properties', {}), ensure_ascii=False)}"
        )
        user_content = f"{msg}\n\n{format_instruction}"

        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": user_content},
        ]

        # 在线程池中执行同步 LLM 调用，避免阻塞
        raw = await asyncio.to_thread(
            self.llm_client.think,
            messages=messages,
            temperature=0.3,
        )
        if not raw:
            return structured_model()

        # 从回复中抽取 JSON（兼容被 markdown 包裹的情况）
        text = raw.strip()
        json_match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
        try:
            data = json.loads(text)
            return structured_model.model_validate(data)
        except (json.JSONDecodeError, Exception) as e:
            print(f"  [解析 {self.name} 回复失败] {e}，使用默认响应")
            return structured_model()


class ModeratorAgent:
    """
    主持人智能体：不调用 LLM，仅根据阶段生成公告文案并返回。
    游戏控制层通过 moderator.announce(text) 获取要广播的字符串。
    """

    def __init__(self):
        self.name = "主持人"

    async def announce(self, text: str) -> str:
        """返回公告内容（可直接作为 MsgHub 的 announcement 或 fanout 的 msg）。"""
        return text


def create_player_agent(
    name: str,
    role: str,
    character: str,
    llm_client: Any,
) -> PlayerAgent:
    """工厂方法：创建一名玩家智能体。"""
    return PlayerAgent(
        name=name,
        role=role,
        character=character,
        llm_client=llm_client,
    )


def create_moderator_agent() -> ModeratorAgent:
    """工厂方法：创建主持人智能体。"""
    return ModeratorAgent()
