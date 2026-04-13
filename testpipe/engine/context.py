"""Execution context objects."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from testpipe.infra import ArtifactStore, DeviceExecutor, HostExecutor, TransferExecutor


class MappingView:
    """Read-only convenience wrapper."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def require(self, key: str) -> Any:
        if key not in self._data:
            raise KeyError(f"missing required key: {key}")
        return self._data[key]

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)


class ExecutionContext:
    """Case-scoped execution state."""

    def __init__(self, *, case_spec, pipeline_spec, env_profile, run_dir: Path, trace_recorder, debug: bool) -> None:
        self.case_spec = case_spec
        self.pipeline_spec = pipeline_spec
        self.env_profile = env_profile
        self.run_dir = run_dir
        self.trace_recorder = trace_recorder
        self.debug = debug
        self.artifact_store = ArtifactStore(run_dir / "resources")
        self.shared_data: dict[str, Any] = dict(case_spec.inputs)
        self.node_outputs: dict[str, dict[str, Any]] = {}

    def set_node_outputs(self, node_name: str, outputs: dict[str, Any]) -> None:
        self.node_outputs[node_name] = dict(outputs)
        self.shared_data.update(outputs)

    def write_snapshot(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        if not self.debug:
            return
        (self.run_dir / "case_spec.yaml").write_text(
            yaml.safe_dump(self.case_spec.to_dict(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        (self.run_dir / "pipeline_spec.json").write_text(
            json.dumps(self.pipeline_spec.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (self.run_dir / "env_profile.json").write_text(
            json.dumps(self.env_profile.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


@dataclass(slots=True)
class StepContext:
    """Step-scoped execution state exposed to TestOp."""

    node_name: str
    step_dir: str
    stdout_log_path: str
    stderr_log_path: str
    inputs: MappingView
    attrs: MappingView
    host: HostExecutor
    device: DeviceExecutor | None
    transfer: TransferExecutor | None
    artifacts: ArtifactStore
    logger_name: str
    debug: bool

    def to_step_record(self, *, status: str, op_type: str, outputs: dict[str, Any], duration_ms: int) -> dict[str, Any]:
        return {
            "step_name": self.node_name,
            "op_type": op_type,
            "status": status,
            "duration_ms": duration_ms,
            "inputs": sorted(self.inputs.to_dict().keys()),
            "outputs": sorted(outputs.keys()),
        }
