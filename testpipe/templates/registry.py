"""Registries for built-in and user-defined LLM templates."""

from __future__ import annotations

from testpipe.core.exceptions import ValidationError
from testpipe.spec import TemplateSpec

_TEMPLATES: dict[str, TemplateSpec] = {}


def register_template(template: TemplateSpec) -> TemplateSpec:
    if template.name in _TEMPLATES:
        raise ValidationError(f"duplicate template: {template.name}")
    _TEMPLATES[template.name] = template
    return template


def get_template(name: str) -> TemplateSpec:
    if name not in _TEMPLATES:
        raise ValidationError(f"unknown template: {name}")
    return _TEMPLATES[name]


def list_templates() -> list[str]:
    return sorted(_TEMPLATES.keys())
