"""示例 Skill 插件入口。"""
from __future__ import annotations

from core.runtime.skill_loader import SkillDefinition


def create_skill() -> SkillDefinition:
    return SkillDefinition(
        id="example-skill",
        intent_description="翻译 translate 翻訳",
        system_prompt_addendum="你是一个专业翻译助手。请将用户输入翻译为目标语言。如果未指定目标语言，默认翻译为英文。",
        tool_allowlist=["search"],
    )
