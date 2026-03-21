"""消息系统：统一智能体与 LLM 之间的对话条目格式。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator

MessageRole = Literal["user", "assistant", "system", "tool"]


class Message(BaseModel):
    """框架内标准消息；`to_dict` 输出与 OpenAI Chat Completions 消息字典兼容。"""

    content: str
    role: MessageRole
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata", mode="before")
    @classmethod
    def _none_metadata_to_dict(cls, v: Any) -> Any:
        if v is None:
            return {}
        return v

    def to_dict(self) -> Dict[str, Any]:
        """转换为 OpenAI API 使用的消息字典（role + content）。"""
        return {"role": self.role, "content": self.content}

    def __str__(self) -> str:
        return f"[{self.role}] {self.content}"
