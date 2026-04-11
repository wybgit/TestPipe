"""Execution results and expectation evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class ResultSummary:
    case_id: str
    pipeline: str
    status: str
    started_at: str
    ended_at: str
    duration_ms: int
    outputs: dict[str, Any]
    failed_step: str | None = None
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_expected(expected: dict[str, Any], outputs: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key, expected_value in expected.items():
        actual = outputs.get(key)
        if isinstance(expected_value, str) and expected_value[:2] in {">=", "<=", "==", "!="}:
            operator = expected_value[:2]
            rhs = float(expected_value[2:].strip())
            lhs = float(actual)
            ok = {
                ">=": lhs >= rhs,
                "<=": lhs <= rhs,
                "==": lhs == rhs,
                "!=": lhs != rhs,
            }[operator]
            if not ok:
                issues.append(f"{key} expected {expected_value}, got {actual}")
        elif isinstance(expected_value, str) and expected_value[:1] in {">", "<"}:
            operator = expected_value[:1]
            rhs = float(expected_value[1:].strip())
            lhs = float(actual)
            ok = {">": lhs > rhs, "<": lhs < rhs}[operator]
            if not ok:
                issues.append(f"{key} expected {expected_value}, got {actual}")
        elif actual != expected_value:
            issues.append(f"{key} expected {expected_value!r}, got {actual!r}")
    return issues


def now_iso() -> str:
    return datetime.now(UTC).isoformat()
