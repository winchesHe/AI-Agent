"""工具参数元数据：用于自描述与 OpenAI function schema 生成。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ToolParameter(BaseModel):
    """单参数定义，供 `get_parameters` 与 schema 构建使用。"""

    name: str
    type: str = "string"
    description: str = ""
    required: bool = True
    default: Any = None

    model_config = {"frozen": True}
