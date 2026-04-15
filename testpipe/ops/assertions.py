"""Assertion operators."""

from __future__ import annotations

from pathlib import Path

from testpipe.core import TestOp, register_op
from testpipe.spec import AttrSpec, OpSpec, PortSpec


@register_op
class PathExistsOp(TestOp):
    """Check whether a local path exists."""

    spec = OpSpec(
        version="1.0",
        description="Check whether a local file or directory exists",
        inputs=[PortSpec(name="target_path", type="artifact:path", description="path to inspect")],
        outputs=[
            PortSpec(name="path_exists", type="bool", description="path existence result"),
            PortSpec(name="checked_path", type="artifact:path", description="normalized checked path", expose=False),
        ],
        attrs=[],
    )

    def execute(self, step_context) -> dict[str, bool | str]:
        target_path = Path(str(step_context.inputs.require("target_path"))).expanduser().resolve()
        return {
            "path_exists": target_path.exists(),
            "checked_path": str(target_path),
        }


@register_op
class ValueCompareOp(TestOp):
    """Compare an input value against a configured expected value."""

    spec = OpSpec(
        version="1.0",
        description="Compare an actual value against an expected value using a configured operator",
        inputs=[
            PortSpec(name="actual_value", type="any", description="actual value to compare"),
            PortSpec(name="expected_value", type="any", required=False, description="expected comparison value"),
            PortSpec(name="operator", type="string", required=False, description="comparison operator"),
        ],
        outputs=[
            PortSpec(name="test_passed", type="bool", description="comparison result"),
            PortSpec(name="comparison_detail", type="string", description="comparison detail", expose=False),
        ],
        attrs=[
            AttrSpec(
                name="operator",
                type="string",
                required=False,
                default="eq",
                enum=["eq", "ne", "gt", "ge", "lt", "le"],
                description="comparison operator",
            ),
            AttrSpec(name="expected_value", type="any", required=True, description="expected comparison value"),
        ],
    )

    def execute(self, step_context) -> dict[str, bool | str]:
        actual = step_context.inputs.require("actual_value")
        expected = step_context.inputs.get("expected_value", step_context.attrs.require("expected_value"))
        operator = str(step_context.inputs.get("operator", step_context.attrs.get("operator", "eq")))

        if operator in {"eq", "ne"}:
            passed = actual == expected if operator == "eq" else actual != expected
        else:
            lhs = self._to_float(actual)
            rhs = self._to_float(expected)
            passed = {
                "gt": lhs > rhs,
                "ge": lhs >= rhs,
                "lt": lhs < rhs,
                "le": lhs <= rhs,
            }[operator]

        detail = f"operator={operator}, expected={expected!r}, actual={actual!r}"
        return {
            "test_passed": passed,
            "comparison_detail": detail,
        }

    def _to_float(self, value: object) -> float:
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"value is not numeric: {value!r}") from exc
