"""Registries for ops and pipelines."""

from __future__ import annotations

from typing import Type

from testpipe.core.exceptions import ValidationError

_OPS: dict[str, Type] = {}
_PIPELINES: dict[str, Type] = {}


def register_op(op_class: Type) -> Type:
    spec = getattr(op_class, "spec", None)
    if spec is None:
        raise ValidationError(f"{op_class.__name__} must define spec")
    if spec.op_type in _OPS:
        raise ValidationError(f"duplicate op type: {spec.op_type}")
    _OPS[spec.op_type] = op_class
    return op_class


def get_op_class(op_type: str) -> Type:
    if op_type not in _OPS:
        raise ValidationError(f"unknown op type: {op_type}")
    return _OPS[op_type]


def register_pipeline(pipeline_class: Type) -> Type:
    name = pipeline_class.__name__
    if name in _PIPELINES:
        raise ValidationError(f"duplicate pipeline: {name}")
    _PIPELINES[name] = pipeline_class
    return pipeline_class


def create_pipeline(name: str):
    if name not in _PIPELINES:
        raise ValidationError(f"unknown pipeline: {name}")
    return _PIPELINES[name]()


def list_pipelines() -> list[str]:
    return sorted(_PIPELINES.keys())
