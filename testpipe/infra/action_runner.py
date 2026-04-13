"""Run tracked external actions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
import shlex
import shutil
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

    def _run_subprocess(
        self,
        command: str | list[str],
        *,
        action_type: str,
        target: str,
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
        result = ActionResult(
            action_type=action_type,
            target=target,
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            started_at=started_at.isoformat(),
            ended_at=ended_at.isoformat(),
            duration_ms=int((ended_at - started_at).total_seconds() * 1000),
        )
        self._append_step_log(
            stdout_log,
            title=f"{action_type} | target={target} | rc={result.returncode} | {result.duration_ms}ms",
            command=command,
            content=completed.stdout or "",
        )
        self._append_step_log(
            stderr_log,
            title=f"{action_type} | target={target} | rc={result.returncode} | {result.duration_ms}ms",
            command=command,
            content=completed.stderr or "",
        )
        self.trace_recorder.record(
            step_name=step_name,
            action_type=result.action_type,
            request={
                "command": command,
                "cwd": cwd,
                "timeout": timeout,
                "target": target,
            },
            response=result.to_dict(),
        )
        return result

    def _append_step_log(
        self,
        output_path: Path,
        *,
        title: str,
        command: str | list[str],
        content: str,
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        rendered_command = command if isinstance(command, str) else shlex.join([str(item) for item in command])
        payload = "\n".join(
            [
                "=" * 72,
                title,
                f"command: {rendered_command}",
                "-" * 72,
                content.rstrip(),
                "",
            ]
        )
        with output_path.open("a", encoding="utf-8") as handle:
            handle.write(payload)

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
        return self._run_subprocess(
            command,
            action_type="host.exec",
            target="local",
            step_name=step_name,
            stdout_log=stdout_log,
            stderr_log=stderr_log,
            cwd=cwd,
            env=env,
            timeout=timeout,
        )

    def run_device(
        self,
        command: str | list[str],
        *,
        target: str,
        step_name: str,
        stdout_log: Path,
        stderr_log: Path,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> ActionResult:
        return self._run_subprocess(
            command,
            action_type="device.exec",
            target=target,
            step_name=step_name,
            stdout_log=stdout_log,
            stderr_log=stderr_log,
            cwd=cwd,
            env=env,
            timeout=timeout,
        )

    def copy_file(
        self,
        source: str | Path,
        destination: str | Path,
        *,
        action_type: str,
        target: str,
        step_name: str,
        stdout_log: Path | None = None,
        stderr_log: Path | None = None,
    ) -> ActionResult:
        source_path = Path(source)
        destination_path = Path(destination)
        started_at = datetime.now(UTC)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
        ended_at = datetime.now(UTC)
        result = ActionResult(
            action_type=action_type,
            target=target,
            command=None,
            returncode=0,
            stdout=str(destination_path),
            stderr="",
            started_at=started_at.isoformat(),
            ended_at=ended_at.isoformat(),
            duration_ms=int((ended_at - started_at).total_seconds() * 1000),
            artifacts=[str(destination_path)],
        )
        if stdout_log is not None:
            self._append_step_log(
                stdout_log,
                title=f"{action_type} | target={target} | rc={result.returncode} | {result.duration_ms}ms",
                command=["cp", str(source_path), str(destination_path)],
                content=str(destination_path),
            )
        if stderr_log is not None:
            self._append_step_log(
                stderr_log,
                title=f"{action_type} | target={target} | rc={result.returncode} | {result.duration_ms}ms",
                command=["cp", str(source_path), str(destination_path)],
                content="",
            )
        self.trace_recorder.record(
            step_name=step_name,
            action_type=action_type,
            request={
                "source": str(source_path),
                "destination": str(destination_path),
                "target": target,
            },
            response=result.to_dict(),
        )
        return result
