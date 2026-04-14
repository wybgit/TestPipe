"""Primary execution engine."""

from __future__ import annotations

import json
import shlex
import textwrap
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from testpipe.core import StepExecutionError, get_op_class
from testpipe.core.registry import get_op_folder
from testpipe.engine.context import ExecutionContext, MappingView, StepContext
from testpipe.engine.planner import ExecutionPlanner
from testpipe.engine.result import ResultSummary, evaluate_expected
from testpipe.infra import ActionRunner, DeviceExecutor, HostExecutor, TraceRecorder, TransferExecutor

try:
    from rich.console import Console
    from rich.panel import Panel
except ImportError:  # pragma: no cover - optional dependency
    Console = None  # type: ignore[assignment]
    Panel = None  # type: ignore[assignment]


class TestEngine:
    """Execute CaseSpec against a compiled PipelineSpec."""

    def __init__(self, output_root: str | Path = "runs", *, debug: bool = False) -> None:
        self.output_root = Path(output_root)
        self.debug = debug
        self._console = Console(highlight=False) if Console is not None else None

    def execute(self, case_spec, pipeline_spec, env_profile) -> ResultSummary:
        started_at = datetime.now(UTC)
        run_dir = self.output_root / f"{case_spec.case_id}_{started_at.strftime('%Y%m%d_%H%M%S')}"
        execution_log_path = run_dir / "execution.log"
        trace_recorder = TraceRecorder(run_dir / "trace.json")
        context = ExecutionContext(
            case_spec=case_spec,
            pipeline_spec=pipeline_spec,
            env_profile=env_profile,
            run_dir=run_dir,
            trace_recorder=trace_recorder,
            debug=self.debug,
        )
        context.write_snapshot()
        plan = ExecutionPlanner().build(pipeline_spec)
        failed_step: str | None = None
        step_error: Exception | None = None

        try:
            for step in plan:
                node_spec = pipeline_spec.node_map()[step.node_name]
                op_class = get_op_class(node_spec.op)
                op = op_class(**node_spec.attrs)
                step_dir = run_dir / "steps" / f"{step.index:02d}_{step.node_name}"
                step_dir.mkdir(parents=True, exist_ok=True)
                stdout_log = step_dir / "stdout.log"
                stderr_log = step_dir / "stderr.log"

                collected_inputs = self._collect_inputs(pipeline_spec, node_spec.name, context)
                display_inputs = self._filter_step_inputs(op_class, collected_inputs)
                action_runner = ActionRunner(trace_recorder)
                host_executor = HostExecutor(action_runner, None)  # type: ignore[arg-type]
                device_executor = DeviceExecutor(action_runner, env_profile, None, run_dir)  # type: ignore[arg-type]
                transfer_executor = TransferExecutor(action_runner, env_profile, None, run_dir)  # type: ignore[arg-type]
                step_context = StepContext(
                    node_name=node_spec.name,
                    step_dir=str(step_dir),
                    stdout_log_path=str(stdout_log),
                    stderr_log_path=str(stderr_log),
                    inputs=MappingView(collected_inputs),
                    attrs=MappingView(node_spec.attrs),
                    host=host_executor,
                    device=device_executor if device_executor.enabled() else None,
                    transfer=transfer_executor if transfer_executor.enabled() else None,
                    artifacts=context.artifact_store,
                    logger_name=f"{pipeline_spec.name}.{node_spec.name}",
                    debug=self.debug,
                )
                step_context.host.step_context = step_context
                if step_context.device is not None:
                    step_context.device.step_context = step_context
                if step_context.transfer is not None:
                    step_context.transfer.step_context = step_context
                    step_context.transfer.device.step_context = step_context

                visible_outputs = self._visible_output_names(op_class)
                event_offset = len(trace_recorder.events)
                step_started = perf_counter()
                outputs: dict[str, object] = {}
                status = "passed"
                failure_message: str | None = None

                try:
                    op.setup(step_context)
                    outputs = op.execute(step_context)
                    context.set_node_outputs(node_spec.name, outputs)
                except Exception as exc:  # noqa: BLE001
                    status = "failed"
                    failed_step = node_spec.name
                    failure_message = str(exc)
                    self._append_step_error(stderr_log, failure_message)
                    step_error = StepExecutionError(node_spec.name, failure_message)
                finally:
                    step_events = trace_recorder.events[event_offset:]
                    try:
                        op.teardown(step_context)
                    except Exception as teardown_exc:  # noqa: BLE001
                        self._append_step_error(stderr_log, f"[teardown] {teardown_exc}")
                    duration_ms = int((perf_counter() - step_started) * 1000)
                    rendered_outputs = self._select_visible_outputs(outputs, visible_outputs)
                    node_type = self._node_type_label(pipeline_spec, node_spec, step, op_class)
                    checks = self._build_checks(node_spec, op_class, display_inputs, rendered_outputs)
                    step_result = self._build_step_result(
                        step=step,
                        total_steps=len(plan),
                        node_spec=node_spec,
                        node_type=node_type,
                        step_inputs=display_inputs,
                        step_events=step_events,
                        outputs=rendered_outputs,
                        checks=checks,
                        duration_ms=duration_ms,
                        status=status,
                        failure_message=failure_message,
                    )
                    self._emit_step_block(execution_log_path, step_result)
                    self._write_step_files(step_dir, step_result, step_events)

                    if self.debug:
                        (step_dir / "step.json").write_text(
                            json.dumps(step_result, indent=2, ensure_ascii=False),
                            encoding="utf-8",
                        )

                if step_error is not None:
                    break
        finally:
            outputs = {item.name: context.shared_data.get(item.name) for item in pipeline_spec.outputs}
            issues = evaluate_expected(case_spec.expected, outputs)
            if step_error is not None:
                issues.append(str(step_error))
            ended_at = datetime.now(UTC)
            summary = ResultSummary(
                case_id=case_spec.case_id,
                case_name=case_spec.name,
                pipeline=pipeline_spec.name,
                status="passed" if not issues else "failed",
                duration_ms=int((ended_at - started_at).total_seconds() * 1000),
                run_dir=str(run_dir),
                outputs=outputs,
                started_at=started_at.isoformat(),
                ended_at=ended_at.isoformat(),
                failed_step=failed_step,
                issues=issues,
            )
            (run_dir / "summary.json").write_text(
                json.dumps(summary.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            (run_dir / "summary.internal.json").write_text(
                json.dumps(summary.to_internal_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            self._print_case_summary(summary)
            if self.debug:
                self._write_reproduce_script(run_dir, trace_recorder)
                trace_recorder.save()
        return summary

    def _build_step_result(
        self,
        *,
        step,
        total_steps: int,
        node_spec,
        node_type: str,
        step_inputs: dict[str, object],
        step_events,
        outputs: dict[str, object],
        checks: dict[str, object],
        duration_ms: int,
        status: str,
        failure_message: str | None,
    ) -> dict[str, Any]:
        return {
            "step_index": step.index,
            "total_steps": total_steps,
            "step_name": node_spec.name,
            "op": node_spec.op,
            "node_type": node_type,
            "status": status,
            "duration_ms": duration_ms,
            "inputs": step_inputs,
            "params": dict(node_spec.attrs),
            "commands": self._build_step_commands(node_spec.op, step_inputs, step_events),
            "execution_logs": self._build_execution_logs(node_spec.op, step_events),
            "outputs": outputs,
            "checks": checks,
            "error": failure_message,
        }

    def _emit_step_block(self, execution_log_path: Path, step_result: dict[str, Any]) -> None:
        body_lines = self._render_step_body(step_result)
        if step_result["error"]:
            body_lines.append(f"error: {step_result['error']}")

        marker = "PASS" if step_result["status"] == "passed" else "FAIL"
        header = (
            f"[{marker}][{step_result['node_type']}] "
            f"{step_result['step_index']}/{step_result['total_steps']} "
            f"{step_result['step_name']} ({step_result['op']}) | {step_result['duration_ms']}ms"
        )
        self._emit_block(
            execution_log_path,
            header=header,
            body_lines=body_lines,
            kind="step_pass" if step_result["status"] == "passed" else "step_fail",
        )

    def _collect_inputs(self, pipeline_spec, node_name: str, context: ExecutionContext) -> dict[str, object]:
        node_spec = pipeline_spec.node_map()[node_name]
        inputs: dict[str, object] = {}
        for binding in node_spec.input_bindings:
            if binding.source_kind == "pipeline_input":
                if binding.source_name in context.shared_data:
                    inputs[binding.input_name] = context.shared_data[binding.source_name]
                continue
            if binding.source_kind == "node_output":
                source_outputs = context.node_outputs.get(binding.source_name, {})
                if binding.source_port in source_outputs:
                    inputs[binding.input_name] = source_outputs[binding.source_port]
        return inputs

    def _filter_step_inputs(self, op_class, inputs: dict[str, object]) -> dict[str, object]:
        allowed = {item.name for item in op_class.spec.inputs}
        if not allowed:
            return {}
        return {key: value for key, value in inputs.items() if key in allowed}

    def _write_reproduce_script(self, run_dir: Path, trace_recorder: TraceRecorder) -> None:
        lines = ["#!/usr/bin/env bash", "set -euo pipefail", ""]
        for event in trace_recorder.events:
            rendered = self._render_event_command(event)
            if rendered:
                lines.append(f"# step: {event.step_name}")
                lines.append(rendered)
                lines.append("")
        script_path = run_dir / "reproduce.sh"
        script_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    def _write_step_files(self, step_dir: Path, step_result: dict[str, Any], step_events) -> None:
        body_lines = self._render_step_body(step_result)
        if step_result["error"]:
            body_lines.append(f"error: {step_result['error']}")
        marker = "PASS" if step_result["status"] == "passed" else "FAIL"
        text = self._render_block_text(
            header=(
                f"[{marker}][{step_result['node_type']}] "
                f"{step_result['step_index']}/{step_result['total_steps']} "
                f"{step_result['step_name']} ({step_result['op']}) | {step_result['duration_ms']}ms"
            ),
            body_lines=body_lines,
        )
        (step_dir / "execution.log").write_text(text + "\n", encoding="utf-8")
        (step_dir / "result.json").write_text(json.dumps(step_result, indent=2, ensure_ascii=False), encoding="utf-8")
        self._write_step_command_script(step_dir, step_events)

    def _write_step_command_script(self, step_dir: Path, step_events) -> None:
        rendered_commands = [self._render_event_command(event) for event in step_events]
        commands = [item for item in rendered_commands if item]
        if not commands:
            return
        lines = ["#!/usr/bin/env bash", "set -euo pipefail", ""]
        for index, command in enumerate(commands, start=1):
            lines.append(f"# action {index}")
            lines.append(command)
            lines.append("")
        script_path = step_dir / "command.sh"
        script_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        script_path.chmod(0o755)

    def _emit_block(
        self,
        execution_log_path: Path,
        *,
        header: str,
        body_lines: list[str],
        kind: str,
    ) -> None:
        text = self._render_block_text(header=header, body_lines=body_lines)
        execution_log_path.parent.mkdir(parents=True, exist_ok=True)
        with execution_log_path.open("a", encoding="utf-8") as handle:
            handle.write(text)
            handle.write("\n")
        self._print_console_block(header=header, body_lines=body_lines, kind=kind, fallback_text=text)

    def _render_block_text(self, *, header: str, body_lines: list[str]) -> str:
        lines = [self._divider("="), header]
        if body_lines:
            lines.append(self._divider("-"))
            lines.extend(body_lines)
        return "\n".join(lines)

    def _print_case_summary(self, summary: ResultSummary) -> None:
        body_lines = [
            f"case_id: {summary.case_id}",
            f"case_name: {summary.case_name}",
            f"pipeline: {summary.pipeline}",
            f"status: {summary.status}",
            f"duration_ms: {summary.duration_ms}",
            f"run_dir: {summary.run_dir}",
        ]
        header = f"[SUMMARY] {summary.case_id}"
        fallback_text = self._render_block_text(header=header, body_lines=body_lines)
        self._print_console_block(
            header=header,
            body_lines=body_lines,
            kind="case_summary",
            fallback_text=fallback_text,
        )

    def _print_console_block(self, *, header: str, body_lines: list[str], kind: str, fallback_text: str) -> None:
        if self._console is None or Panel is None:
            print(fallback_text)
            return
        node_type = self._header_node_type(header)
        style = self._style_for(kind, node_type)
        body = "\n".join(body_lines) if body_lines else " "
        self._console.print(
            Panel(
                body,
                title=header,
                border_style=style,
                padding=(0, 1),
                expand=True,
            )
        )

    def _style_for(self, kind: str, node_type: str | None) -> str:
        if kind in {"step_fail", "case_fail"}:
            return "bold red"
        if kind == "case_summary":
            return "bold magenta"
        if node_type == "INPUT":
            return "cyan"
        if node_type == "EXEC":
            return "blue"
        if node_type == "OUTPUT":
            return "green"
        return "white"

    def _header_node_type(self, header: str) -> str | None:
        if "[INPUT]" in header:
            return "INPUT"
        if "[EXEC]" in header:
            return "EXEC"
        if "[OUTPUT]" in header:
            return "OUTPUT"
        return None

    def _node_type_label(self, pipeline_spec, node_spec, step, op_class) -> str:
        if get_op_folder(op_class) == "asserts":
            return "OUTPUT"
        has_downstream = any(edge.source_node == node_spec.name for edge in pipeline_spec.edges)
        if not step.depends_on and has_downstream:
            return "INPUT"
        return "EXEC"

    def _render_step_body(self, step_result: dict[str, Any]) -> list[str]:
        node_type = str(step_result["node_type"])
        if node_type == "INPUT":
            return self._format_section("I", step_result["inputs"])
        if node_type == "EXEC":
            body_lines = self._format_section("I", step_result["inputs"])
            body_lines.extend(self._format_behavior_section(step_result["commands"], step_result["execution_logs"]))
            body_lines.extend(self._format_section("O", step_result["outputs"]))
            return body_lines
        body_lines = self._format_section("O", step_result["outputs"])
        body_lines.extend(self._format_section("CHECK", step_result["checks"]))
        return body_lines

    def _build_checks(self, node_spec, op_class, step_inputs: dict[str, object], outputs: dict[str, object]) -> dict[str, object]:
        if get_op_folder(op_class) != "asserts":
            return {}

        checks: dict[str, object] = {}
        for key in ("target_path", "actual_text", "expected_text", "actual_value", "expected_json", "json_data"):
            if key in step_inputs:
                checks[key] = step_inputs[key]
        for key in ("expected_value", "operator", "expectations"):
            if key in node_spec.attrs:
                checks[key] = node_spec.attrs[key]
        if "test_passed" in outputs:
            checks["check_result"] = outputs["test_passed"]
        elif "path_exists" in outputs:
            checks["check_result"] = outputs["path_exists"]
        return checks

    def _build_step_commands(self, op: str, step_inputs: dict[str, object], step_events) -> list[str]:
        commands = [item for item in (self._render_event_command(event) for event in step_events) if item]
        if self.debug or op != "ResourceFetch":
            return commands

        resource_ref = step_inputs.get("resource_ref")
        if isinstance(resource_ref, dict):
            repo = resource_ref.get("repo", "")
            git_ref = resource_ref.get("ref", "HEAD")
            subpath = resource_ref.get("subpath", "")
            return [
                f"git sparse-fetch repo={repo} ref={git_ref} subpath={subpath} (full git commands hidden; use --debug)"
            ]

        resource_path = step_inputs.get("resource_path")
        if resource_path is not None:
            return [f"fetch local resource path={resource_path}"]
        return commands

    def _build_execution_logs(self, op: str, step_events) -> dict[str, str]:
        if not self.debug and op == "ResourceFetch":
            if not step_events:
                return {}
            last_event = step_events[-1]
            stderr_preview = self._preview_stream(str(last_event.response.get("stderr", "")))
            if stderr_preview:
                return {"process stderr": stderr_preview}
            return {}

        logs: dict[str, str] = {}
        total = len(step_events)
        for index, event in enumerate(step_events, start=1):
            action_label = f"action_{index}" if total > 1 else "process"
            suffix = f" ({event.action_type})" if total > 1 else ""
            stdout_preview = self._preview_stream(str(event.response.get("stdout", "")))
            stderr_preview = self._preview_stream(str(event.response.get("stderr", "")))
            if stdout_preview:
                logs[f"{action_label}{suffix} stdout"] = stdout_preview
            if stderr_preview:
                logs[f"{action_label}{suffix} stderr"] = stderr_preview
        return logs

    def _preview_stream(self, content: str, *, max_lines: int = 12, max_chars: int = 800) -> str | None:
        normalized = content.strip()
        if not normalized:
            return None
        lines = normalized.splitlines()
        preview_lines = lines[:max_lines]
        preview = "\n".join(preview_lines)
        truncated = len(lines) > max_lines or len(preview) > max_chars
        if len(preview) > max_chars:
            preview = preview[:max_chars].rstrip()
        if truncated:
            preview = preview.rstrip() + "\n...[truncated]"
        return preview

    def _format_section(self, title: str, payload: dict[str, Any]) -> list[str]:
        if not payload:
            return []
        lines = [f"{title}:"]
        for key, value in payload.items():
            lines.append(f"  - {key}: {self._render_value(value)}")
        return lines

    def _format_list_section(self, title: str, values: list[Any]) -> list[str]:
        if not values:
            return []
        lines = [f"{title}:"]
        for item in values:
            lines.append(f"  - {self._render_value(item)}")
        return lines

    def _format_behavior_section(self, commands: list[str], logs: dict[str, str]) -> list[str]:
        if not commands and not logs:
            return []
        lines = ["B:"]
        for command in commands:
            lines.extend(self._indent_wrapped(f"command: {command}", prefix="  - "))
        for key, value in logs.items():
            lines.append(f"  - {key}:")
            lines.extend(self._indent_block(value, prefix="      "))
        return lines

    def _render_value(self, value: Any) -> str:
        rendered = repr(value)
        if len(rendered) > 180:
            rendered = rendered[:177] + "..."
        return rendered

    def _visible_output_names(self, op_class) -> set[str]:
        return {item.name for item in op_class.spec.outputs if getattr(item, "expose", True)}

    def _select_visible_outputs(self, outputs: dict[str, Any], visible_output_names: set[str]) -> dict[str, Any]:
        return {key: value for key, value in outputs.items() if key in visible_output_names}

    def _indent_wrapped(self, text: str, *, prefix: str, width: int = 100) -> list[str]:
        wrapped = textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False)
        if not wrapped:
            return [prefix.rstrip()]
        return [f"{prefix}{line}" if index == 0 else f"{' ' * len(prefix)}{line}" for index, line in enumerate(wrapped)]

    def _indent_block(self, text: str, *, prefix: str) -> list[str]:
        return [f"{prefix}{line}" for line in text.splitlines()] or [prefix.rstrip()]

    def _append_step_error(self, output_path: Path, message: str) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("a", encoding="utf-8") as handle:
            handle.write(message.rstrip())
            handle.write("\n")

    def _render_event_command(self, event) -> str | None:
        command = event.request.get("command")
        if command:
            return command if isinstance(command, str) else shlex.join([str(item) for item in command])
        source = event.request.get("source")
        destination = event.request.get("destination")
        if source and destination:
            return f"cp {source} {destination}"
        return None

    def _divider(self, char: str) -> str:
        return char * 96
