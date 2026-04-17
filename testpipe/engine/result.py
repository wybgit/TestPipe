"""Execution results and expectation evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ResultSummary:
    case_id: str
    description: str
    level: str
    pipeline: str
    status: str
    duration_ms: int
    run_dir: str
    outputs: dict[str, Any] = field(default_factory=dict)
    started_at: str = ""
    ended_at: str = ""
    failed_step: str | None = None
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "description": self.description,
            "level": self.level,
            "pipeline": self.pipeline,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "run_dir": self.run_dir,
        }

    def to_internal_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_expected(expected: dict[str, Any], outputs: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key, expected_value in expected.items():
        actual = outputs.get(key)
        if isinstance(expected_value, dict):
            issues.extend(_evaluate_mapping_expected(key, expected_value, actual))
            continue
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


def _evaluate_mapping_expected(key: str, expected_value: dict[str, Any], actual: Any) -> list[str]:
    issues: list[str] = []
    supported = {"equals", "exists"}
    unknown = sorted(token for token in expected_value if token not in supported)
    if unknown:
        issues.append(f"{key} has unsupported expectation keys: {', '.join(unknown)}")
        return issues

    if "equals" in expected_value and actual != expected_value["equals"]:
        issues.append(f"{key} expected {expected_value['equals']!r}, got {actual!r}")

    if "exists" in expected_value:
        expected_exists = bool(expected_value["exists"])
        actual_exists = actual is not None and Path(str(actual)).expanduser().exists()
        if actual_exists != expected_exists:
            state = "to exist" if expected_exists else "to be absent"
            issues.append(f"{key} expected path {state}, got {actual!r}")
    return issues


def now_iso() -> str:
    return datetime.now(UTC).isoformat()
