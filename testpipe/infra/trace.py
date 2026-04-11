"""Structured action tracing."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class TraceEvent:
    step_name: str
    action_type: str
    request: dict[str, Any]
    response: dict[str, Any]
    recorded_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TraceRecorder:
    """Collect structured trace events and write them to disk."""

    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        self.events: list[TraceEvent] = []

    def record(self, *, step_name: str, action_type: str, request: dict[str, Any], response: dict[str, Any]) -> None:
        self.events.append(
            TraceEvent(
                step_name=step_name,
                action_type=action_type,
                request=request,
                response=response,
                recorded_at=datetime.now(UTC).isoformat(),
            )
        )

    def save(self) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(
            json.dumps([event.to_dict() for event in self.events], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
