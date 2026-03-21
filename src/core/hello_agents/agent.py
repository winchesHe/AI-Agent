"""Agent 抽象基类：统一智能体接口与对话历史管理。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from core.llm.llm_client import HelloAgentsLLM

from .config import Config
from .message import Message


class Agent(ABC):
    """所有具体智能体的顶层抽象；子类必须实现 `run`。"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
    ) -> None:
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.config = config or Config()
        self._history: List[Message] = []

    @abstractmethod
    def run(self, input_text: str, **kwargs: object) -> str:
        """执行一轮用户输入并返回文本结果。"""
        ...

    def add_message(self, message: Message) -> None:
        """追加一条消息到历史（不自动截断；截断策略由子类或上层决定）。"""
        self._history.append(message)

    def clear_history(self) -> None:
        """清空历史。"""
        self._history.clear()

    def get_history(self) -> List[Message]:
        """返回历史副本。"""
        return self._history.copy()

    def __str__(self) -> str:
        return f"Agent(name={self.name}, provider={self.llm.provider})"
