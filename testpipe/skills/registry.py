"""Registries for built-in and user-defined LLM skills."""

from __future__ import annotations

from testpipe.core.exceptions import ValidationError
from testpipe.spec import SkillSpec

_SKILLS: dict[str, SkillSpec] = {}


def register_skill(skill: SkillSpec) -> SkillSpec:
    if skill.name in _SKILLS:
        raise ValidationError(f"duplicate skill: {skill.name}")
    _SKILLS[skill.name] = skill
    return skill


def get_skill(name: str) -> SkillSpec:
    if name not in _SKILLS:
        raise ValidationError(f"unknown skill: {name}")
    return _SKILLS[name]


def list_skills() -> list[str]:
    return sorted(_SKILLS.keys())
