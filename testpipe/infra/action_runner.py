"""Run tracked external actions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from subprocess import CompletedProcess, run
from typing import Any


@dataclass(slots=True)
class ActionResult:
    action_type: str
    target: str
    command: str | list[str] | None
    returncode: int | None
    stdout: str = ""
    stderr: str = ""
    started_at: str = ""
    ended_at: str = ""
    duration_ms: int = 0
    artifacts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ActionRunner:
    """Execute and track side-effecting actions."""

    def __init__(self, trace_recorder) -> None:
        self.trace_recorder = trace_recorder

    def run_local(
        self,
        command: str | list[str],
        *,
        step_name: str,
        stdout_log: Path,
        stderr_log: Path,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> ActionResult:
        started_at = datetime.now(UTC)
        completed: CompletedProcess[str] = run(
            command,
            cwd=cwd,
            env=env,
            timeout=timeout,
            capture_output=True,
            text=True,
            check=False,
            shell=isinstance(command, str),
        )
        ended_at = datetime.now(UTC)
        stdout_log.parent.mkdir(parents=True, exist_ok=True)
        stderr_log.parent.mkdir(parents=True, exist_ok=True)
        stdout_log.write_text(completed.stdout or "", encoding="utf-8")
        stderr_log.write_text(completed.stderr or "", encoding="utf-8")
        result = ActionResult(
            action_type="host.exec",
            target="local",
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            started_at=started_at.isoformat(),
            ended_at=ended_at.isoformat(),
            duration_ms=int((ended_at - started_at).total_seconds() * 1000),
        )
        self.trace_recorder.record(
            step_name=step_name,
            action_type=result.action_type,
            request={
                "command": command,
                "cwd": cwd,
                "timeout": timeout,
            },
            response=result.to_dict(),
        )
        return result
