"""Assertion operators."""

from __future__ import annotations

from pathlib import Path

from testpipe.core import TestOp, register_op
from testpipe.spec import AttrSpec, OpSpec, PortSpec


@register_op
class TextEqualsOp(TestOp):
    """Compare two text inputs and emit a business-friendly pass/fail result."""

    spec = OpSpec(
        version="1.0",
        description="Compare actual and expected text content",
        inputs=[
            PortSpec(name="actual_text", type="string", description="actual text content"),
            PortSpec(name="expected_text", type="string", description="expected text content"),
        ],
        outputs=[
            PortSpec(name="test_passed", type="bool", description="comparison result"),
            PortSpec(
                name="mismatch_reason",
                type="string",
                description="comparison mismatch description",
                expose=False,
            ),
        ],
        attrs=[
            AttrSpec(name="strip", type="bool", required=False, default=True, description="strip leading and trailing whitespace"),
            AttrSpec(
                name="normalize_line_endings",
                type="bool",
                required=False,
                default=True,
                description="normalize CRLF/LF differences before comparing",
            ),
        ],
    )

    def execute(self, step_context) -> dict[str, bool | str]:
        actual = self._normalize_text(
            str(step_context.inputs.require("actual_text")),
            strip=bool(step_context.attrs.get("strip", True)),
            normalize_line_endings=bool(step_context.attrs.get("normalize_line_endings", True)),
        )
        expected = self._normalize_text(
            str(step_context.inputs.require("expected_text")),
            strip=bool(step_context.attrs.get("strip", True)),
            normalize_line_endings=bool(step_context.attrs.get("normalize_line_endings", True)),
        )

        if actual == expected:
            return {"test_passed": True, "mismatch_reason": ""}
        return {
            "test_passed": False,
            "mismatch_reason": f"expected {expected!r}, got {actual!r}",
        }

    def _normalize_text(self, value: str, *, strip: bool, normalize_line_endings: bool) -> str:
        if normalize_line_endings:
            value = value.replace("\r\n", "\n").replace("\r", "\n")
        if strip:
            value = value.strip()
        return value


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


@register_op
class JsonObjectAssertOp(TestOp):
    """Assert selected fields inside a JSON object."""

    spec = OpSpec(
        version="1.0",
        description="Validate selected JSON fields against expected values",
        inputs=[
            PortSpec(name="json_data", type="object", description="decoded JSON object"),
            PortSpec(name="expected_json", type="object", required=False, description="expected JSON fields"),
        ],
        outputs=[
            PortSpec(name="test_passed", type="bool", description="assertion result"),
            PortSpec(name="mismatch_reason", type="string", description="assertion mismatch details", expose=False),
        ],
        attrs=[
            AttrSpec(name="expectations", type="object", required=False, default=None, description="fallback expected JSON fields"),
        ],
    )

    def execute(self, step_context) -> dict[str, bool | str]:
        actual = step_context.inputs.require("json_data")
        expectations = step_context.inputs.get("expected_json", step_context.attrs.get("expectations"))
        if expectations is None:
            raise ValueError("expected_json input or expectations attr is required")
        if not isinstance(actual, dict):
            raise ValueError("json_data must be a JSON object")
        if not isinstance(expectations, dict):
            raise ValueError("expected_json/expectations must be a JSON object")

        mismatches: list[str] = []
        for field_path, expected_value in expectations.items():
            actual_value = self._resolve_field(actual, str(field_path))
            if actual_value != expected_value:
                mismatches.append(f"{field_path} expected {expected_value!r}, got {actual_value!r}")

        return {
            "test_passed": not mismatches,
            "mismatch_reason": "; ".join(mismatches),
        }

    def _resolve_field(self, payload: dict[str, object], field_path: str) -> object:
        current: object = payload
        for token in field_path.split("."):
            if isinstance(current, dict):
                if token not in current:
                    return None
                current = current[token]
                continue
            if isinstance(current, list):
                try:
                    index = int(token)
                except ValueError:
                    return None
                if index < 0 or index >= len(current):
                    return None
                current = current[index]
                continue
            return None
        return current
