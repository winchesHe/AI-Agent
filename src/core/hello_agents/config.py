"""配置管理：集中默认参数并支持环境变量覆盖。"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from pydantic import BaseModel


class Config(BaseModel):
    """HelloAgents 框架级配置（与具体脚本中的 .env 约定对齐）。"""

    default_model: str = "gpt-3.5-turbo"
    default_provider: str = "openai"
    temperature: float = 0.7
    max_tokens: Optional[int] = None

    debug: bool = False
    log_level: str = "INFO"

    max_history_length: int = 100

    @classmethod
    def from_env(cls) -> Config:
        """从环境变量创建配置（兼容教材变量名与本仓库 LLM_* 约定）。"""
        max_tok_raw = os.getenv("MAX_TOKENS")
        max_tokens: Optional[int] = None
        if max_tok_raw not in (None, ""):
            max_tokens = int(max_tok_raw)

        return cls(
            default_model=os.getenv("LLM_MODEL_ID")
            or os.getenv("HELLOAGENTS_DEFAULT_MODEL", "gpt-3.5-turbo"),
            default_provider=os.getenv(
                "HELLOAGENTS_DEFAULT_PROVIDER",
                os.getenv("LLM_DEFAULT_PROVIDER", "openai"),
            ),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            temperature=float(
                os.getenv("TEMPERATURE", os.getenv("HELLOAGENTS_TEMPERATURE", "0.7"))
            ),
            max_tokens=max_tokens,
            max_history_length=int(
                os.getenv("HELLOAGENTS_MAX_HISTORY_LENGTH", "100")
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        """序列化为普通字典。"""
        return self.model_dump()
