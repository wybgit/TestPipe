"""Execution backends."""

from __future__ import annotations

from pathlib import Path

from testpipe.core.exceptions import StepExecutionError


class HostExecutor:
    """Local host executor for the initial MVP."""

    def __init__(self, action_runner, step_context) -> None:
        self.action_runner = action_runner
        self.step_context = step_context

    def exec(
        self,
        command: str | list[str],
        *,
        timeout: int | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ):
        result = self.action_runner.run_local(
            command,
            step_name=self.step_context.node_name,
            stdout_log=Path(self.step_context.stdout_log_path),
            stderr_log=Path(self.step_context.stderr_log_path),
            cwd=cwd,
            env=env,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise StepExecutionError(self.step_context.node_name, result.stderr or f"command failed: {command}")
        return result
