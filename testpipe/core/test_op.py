"""Base class for test operators."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from testpipe.core.exceptions import ValidationError
from testpipe.core.registry import get_op_name
from testpipe.spec import AttrSpec, OpSpec


class TestOp(ABC):
    """Base class for all test operators."""

    spec: OpSpec

    def __init__(self, **attrs: Any):
        self.attrs = attrs
        self.validate_attrs()

    @classmethod
    def attr_specs(cls) -> dict[str, AttrSpec]:
        return {item.name: item for item in cls.spec.attrs}

    def validate_attrs(self) -> None:
        op_name = get_op_name(self)
        for item in self.spec.attrs:
            if item.required and item.name not in self.attrs and item.default is None:
                raise ValidationError(f"{op_name} missing required attr: {item.name}")
            if item.enum is not None and item.name in self.attrs and self.attrs[item.name] not in item.enum:
                raise ValidationError(f"{op_name} invalid attr {item.name}: {self.attrs[item.name]}")

    def resolved_attrs(self) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for item in self.spec.attrs:
            if item.name in self.attrs:
                resolved[item.name] = self.attrs[item.name]
            elif item.default is not None:
                resolved[item.name] = item.default
        return resolved

    def setup(self, step_context) -> None:
        """Optional setup hook."""

    @abstractmethod
    def execute(self, step_context) -> dict[str, Any]:
        """Execute the operator and return output values."""

    def teardown(self, step_context) -> None:
        """Optional teardown hook."""
