"""Skill activation: definition model, keyword matching, and manifest loading.

Implements the Skill data model defined in specs/004-openclaw-alignment/data-model.md.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional

import yaml
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class PluginLoadError(Exception):
    """Raised when a plugin manifest cannot be found or parsed.

    Attributes:
        manifest_dir: The directory that was searched.
    """

    def __init__(self, message: str, *, manifest_dir: str | None = None) -> None:
        super().__init__(message)
        self.manifest_dir = manifest_dir


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class SkillDefinition(BaseModel):
    """A single Skill plugin descriptor."""

    id: str
    intent_description: str = Field(
        description="Human-readable keywords / description used for intent matching.",
    )
    system_prompt_addendum: str = Field(
        description="Text injected into the system prompt when this skill is active.",
    )
    tool_allowlist: List[str] = Field(
        default_factory=list,
        description="Names of tools this skill is permitted to invoke.",
    )


# ---------------------------------------------------------------------------
# SkillLoader
# ---------------------------------------------------------------------------

class SkillLoader:
    """Registry of :class:`SkillDefinition` instances with simple keyword matching."""

    def __init__(self, skills: list[SkillDefinition]) -> None:
        self._skills = list(skills)

    # ---- query API ----

    def match_skill(self, user_input: str) -> SkillDefinition | None:
        """Return the first skill whose *intent_description* keywords overlap with *user_input*.

        Matching is case-insensitive.  Each whitespace-delimited token in
        ``intent_description`` is treated as a keyword.
        """
        lower_input = user_input.lower()
        for skill in self._skills:
            keywords = skill.intent_description.lower().split()
            if any(kw in lower_input for kw in keywords):
                return skill
        return None

    def get_skill_by_id(self, skill_id: str) -> SkillDefinition | None:
        """Look up a skill by its ``id``.  Returns *None* if not found."""
        for skill in self._skills:
            if skill.id == skill_id:
                return skill
        return None

    def list_skills(self) -> list[SkillDefinition]:
        """Return all registered skill definitions."""
        return list(self._skills)


# ---------------------------------------------------------------------------
# Manifest loader
# ---------------------------------------------------------------------------

def load_skill_from_manifest(manifest_dir: str) -> SkillDefinition:
    """Load a :class:`SkillDefinition` from a ``skill.json`` or ``skill.yaml`` file.

    Parameters
    ----------
    manifest_dir:
        Directory that should contain ``skill.json`` or ``skill.yaml``.

    Returns
    -------
    SkillDefinition
        The validated skill definition.

    Raises
    ------
    PluginLoadError
        If neither file is found, or the content cannot be parsed / validated.
    """
    base = Path(manifest_dir)
    data: Any = None

    json_path = base / "skill.json"
    yaml_path = base / "skill.yaml"

    if json_path.is_file():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise PluginLoadError(
                f"Failed to read skill.json: {exc}",
                manifest_dir=manifest_dir,
            ) from exc
    elif yaml_path.is_file():
        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            raise PluginLoadError(
                f"Failed to read skill.yaml: {exc}",
                manifest_dir=manifest_dir,
            ) from exc
    else:
        raise PluginLoadError(
            f"No skill.json or skill.yaml found in {manifest_dir}",
            manifest_dir=manifest_dir,
        )

    if not isinstance(data, dict):
        raise PluginLoadError(
            "Skill manifest must be a JSON/YAML mapping",
            manifest_dir=manifest_dir,
        )

    try:
        return SkillDefinition.model_validate(data)
    except Exception as exc:
        raise PluginLoadError(
            f"Skill manifest validation failed: {exc}",
            manifest_dir=manifest_dir,
        ) from exc
