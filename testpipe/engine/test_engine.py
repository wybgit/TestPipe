"""Primary execution engine."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from testpipe.core import StepExecutionError, get_op_class
from testpipe.engine.context import ExecutionContext, MappingView, StepContext
from testpipe.engine.planner import ExecutionPlanner
from testpipe.engine.result import ResultSummary, evaluate_expected
from testpipe.infra import ActionRunner, HostExecutor, TraceRecorder


class TestEngine:
    """Execute CaseSpec against a compiled PipelineSpec."""

    def __init__(self, output_root: str | Path = "runs") -> None:
        self.output_root = Path(output_root)

    def execute(self, case_spec, pipeline_spec, env_profile) -> ResultSummary:
        started_at = datetime.now(UTC)
        run_dir = self.output_root / f"{case_spec.case_id}_{started_at.strftime('%Y%m%d_%H%M%S')}"
        trace_recorder = TraceRecorder(run_dir / "trace.json")
        context = ExecutionContext(
            case_spec=case_spec,
            pipeline_spec=pipeline_spec,
            env_profile=env_profile,
            run_dir=run_dir,
            trace_recorder=trace_recorder,
        )
        context.write_snapshot()
        planner = ExecutionPlanner()
        plan = planner.build(pipeline_spec)
        failed_step: str | None = None
        step_error: Exception | None = None

        try:
            for step in plan:
                node_spec = pipeline_spec.node_map()[step.node_name]
                op_class = get_op_class(node_spec.op_type)
                op = op_class(**node_spec.attrs)
                step_dir = run_dir / "steps" / f"{step.index:02d}_{step.node_name}"
                step_dir.mkdir(parents=True, exist_ok=True)
                stdout_log = step_dir / "stdout.log"
                stderr_log = step_dir / "stderr.log"

                step_inputs = self._collect_inputs(pipeline_spec, node_spec.name, context)
                action_runner = ActionRunner(trace_recorder)
                step_context = StepContext(
                    node_name=node_spec.name,
                    step_dir=str(step_dir),
                    stdout_log_path=str(stdout_log),
                    stderr_log_path=str(stderr_log),
                    inputs=MappingView(step_inputs),
                    attrs=MappingView(node_spec.attrs),
                    host=HostExecutor(action_runner, None),  # type: ignore[arg-type]
                    artifacts=context.artifact_store,
                    logger_name=f"{pipeline_spec.name}.{node_spec.name}",
                )
                step_context.host.step_context = step_context

                step_started = perf_counter()
                outputs: dict[str, object] = {}
                status = "passed"
                try:
                    op.setup(step_context)
                    outputs = op.execute(step_context)
                    context.set_node_outputs(node_spec.name, outputs)
                except Exception as exc:  # noqa: BLE001
                    status = "failed"
                    failed_step = node_spec.name
                    stderr_log.write_text(f"{exc}\n", encoding="utf-8")
                    step_error = StepExecutionError(node_spec.name, str(exc))
                finally:
                    try:
                        op.teardown(step_context)
                    except Exception as teardown_exc:  # noqa: BLE001
                        stderr_log.write_text(
                            (stderr_log.read_text(encoding="utf-8") if stderr_log.exists() else "") + f"\n[teardown] {teardown_exc}\n",
                            encoding="utf-8",
                        )
                    duration_ms = int((perf_counter() - step_started) * 1000)
                    step_record = step_context.to_step_record(
                        status=status,
                        op_type=node_spec.op_type,
                        outputs=outputs,
                        duration_ms=duration_ms,
                    )
                    (step_dir / "step.json").write_text(
                        json.dumps(step_record, indent=2, ensure_ascii=False),
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
                pipeline=pipeline_spec.name,
                status="passed" if not issues else "failed",
                started_at=started_at.isoformat(),
                ended_at=ended_at.isoformat(),
                duration_ms=int((ended_at - started_at).total_seconds() * 1000),
                outputs=outputs,
                failed_step=failed_step,
                issues=issues,
            )
            (run_dir / "summary.json").write_text(
                json.dumps(summary.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            self._write_reproduce_script(run_dir, trace_recorder)
            trace_recorder.save()
        return summary

    def _collect_inputs(self, pipeline_spec, node_name: str, context: ExecutionContext) -> dict[str, object]:
        inputs = {
            item.name: context.shared_data[item.name]
            for item in pipeline_spec.inputs
            if item.name in context.shared_data
        }
        for edge in pipeline_spec.edges:
            if edge.target_node != node_name:
                continue
            source_outputs = context.node_outputs.get(edge.source_node, {})
            if edge.source_port in source_outputs:
                inputs[edge.target_port] = source_outputs[edge.source_port]
        return inputs

    def _write_reproduce_script(self, run_dir: Path, trace_recorder: TraceRecorder) -> None:
        lines = ["#!/usr/bin/env bash", "set -euo pipefail", ""]
        for event in trace_recorder.events:
            command = event.request.get("command")
            if command:
                rendered = command if isinstance(command, str) else " ".join(command)
                lines.append(f"# step: {event.step_name}")
                lines.append(rendered)
                lines.append("")
        script_path = run_dir / "reproduce.sh"
        script_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
