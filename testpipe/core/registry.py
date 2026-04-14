"""Registries for ops and pipelines."""

from __future__ import annotations

from typing import Type

from testpipe.core.exceptions import ValidationError

_OPS: dict[str, Type] = {}
_PIPELINES: dict[str, Type] = {}


def infer_op_name(op_class: Type) -> str:
    name = op_class.__name__
    if name.endswith("Op"):
        return name[:-2]
    return name


def get_op_name(op_or_class: object) -> str:
    op_class = op_or_class if isinstance(op_or_class, type) else op_or_class.__class__
    return str(getattr(op_class, "op_name", infer_op_name(op_class)))


def get_op_group(op_class: Type) -> str:
    module_tokens = op_class.__module__.split(".")
    if "ops" not in module_tokens:
        return ""
    suffix = module_tokens[module_tokens.index("ops") + 1 :]
    if not suffix:
        return ""
    return ".".join(suffix)


def is_assert_op_class(op_class: Type) -> bool:
    return get_op_group(op_class).split(".", 1)[0] == "assertions"


def register_op(op_class: Type) -> Type:
    spec = getattr(op_class, "spec", None)
    if spec is None:
        raise ValidationError(f"{op_class.__name__} must define spec")
    op_name = infer_op_name(op_class)
    if op_name in _OPS:
        raise ValidationError(f"duplicate op name: {op_name}")
    op_class.op_name = op_name
    _OPS[op_name] = op_class
    return op_class


def get_op_class(op_name: str) -> Type:
    if op_name not in _OPS:
        raise ValidationError(f"unknown op name: {op_name}")
    return _OPS[op_name]


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
