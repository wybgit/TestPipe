"""Runtime handlers for built-in skills."""

from __future__ import annotations

import json
import re
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any

import yaml

from testpipe.core import PipelineCompiler, create_pipeline
from testpipe.engine import TestEngine
from testpipe.loaders import EnvProfileLoader, StructuredLoader, TestCaseLoader
from testpipe.skills.registry import get_skill
from testpipe.spec import CaseSpec, EnvProfile, PipelineSpec, PortSpec
from testpipe.validation import CaseChecker


def _snake_case(name: str) -> str:
    normalized = re.sub(r"[\-\s]+", "_", name)
    normalized = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", normalized)
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized.lower()


def _class_case(name: str) -> str:
    tokens = re.split(r"[^0-9A-Za-z]+", name)
    if len(tokens) == 1 and tokens[0]:
        return tokens[0][0].upper() + tokens[0][1:]
    return "".join(token[:1].upper() + token[1:] for token in tokens if token)


def _normalize_port(raw: Any, *, default_type: str = "string") -> dict[str, Any]:
    if isinstance(raw, str):
        return {"name": raw, "type": default_type, "description": ""}
    if isinstance(raw, dict):
        return {
            "name": raw["name"],
            "type": raw.get("type", default_type),
            "description": raw.get("description", ""),
            "required": raw.get("required", True),
            "expose": raw.get("expose", True),
        }
    raise ValueError(f"unsupported port definition: {raw!r}")


def _normalize_ports(raw_ports: list[Any], *, default_type: str = "string") -> list[dict[str, Any]]:
    return [_normalize_port(item, default_type=default_type) for item in raw_ports]


def _render_yaml(payload: dict[str, Any]) -> str:
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False).rstrip()


def _write_text(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return str(path)


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(path)


def _scaffold_config(payload: dict[str, Any]) -> dict[str, Any] | None:
    scaffold = payload.get("scaffold")
    if not isinstance(scaffold, dict):
        return None
    if not scaffold.get("enabled", False):
        return None
    if not scaffold.get("root_dir"):
        raise ValueError("scaffold.root_dir is required when scaffold.enabled=true")
    return scaffold


def _apply_test_op_scaffold(payload: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    scaffold = _scaffold_config(payload)
    if scaffold is None:
        return result
    module_name = _snake_case(result["op_spec"]["name"])
    root_dir = Path(str(scaffold["root_dir"]))
    op_folder = str(result["op_spec"].get("folder", "custom"))
    op_dir = root_dir / str(scaffold.get("ops_dir", "ops")) / op_folder
    tests_dir = root_dir / str(scaffold.get("tests_dir", "tests"))
    docs_dir = root_dir / str(scaffold.get("docs_dir", "docs/ops"))
    result["written_files"] = [
        _write_text(op_dir / f"{module_name}.py", result["python_op_draft"]),
        _write_text(tests_dir / f"test_{module_name}.py", result["unit_test_draft"]),
        _write_text(docs_dir / f"{module_name}.md", result["doc_draft"]),
        _write_json(docs_dir / f"{module_name}.spec.json", result["op_spec"]),
    ]
    return result


def _apply_pipeline_scaffold(payload: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    scaffold = _scaffold_config(payload)
    if scaffold is None:
        return result
    module_name = _snake_case(result["pipeline_spec"]["name"])
    root_dir = Path(str(scaffold["root_dir"]))
    pipelines_dir = root_dir / str(scaffold.get("pipelines_dir", "pipelines"))
    docs_dir = root_dir / str(scaffold.get("docs_dir", "docs/pipelines"))
    result["written_files"] = [
        _write_text(pipelines_dir / f"{module_name}.py", result["python_pipeline_draft"]),
        _write_text(docs_dir / f"{module_name}.mmd", result["mermaid_graph"]),
        _write_json(docs_dir / f"{module_name}.pipeline.json", result["pipeline_spec"]),
    ]
    return result


def _load_case_from_payload(payload: dict[str, Any]) -> CaseSpec:
    if payload.get("case_ref"):
        return TestCaseLoader().load(payload["case_ref"])
    if payload.get("case_spec"):
        raw = payload["case_spec"]
        return CaseSpec(
            case_id=raw.get("case_id", raw["name"]),
            name=raw["name"],
            pipeline=raw["pipeline"],
            inputs=raw.get("inputs", {}),
            expected=raw.get("expected", {}),
            tags=raw.get("tags", []),
            priority=raw.get("priority", "P2"),
            timeout=raw.get("timeout"),
            metadata=raw.get("metadata", {}),
        )
    raise ValueError("case_ref or case_spec is required")


def _dict_to_port_specs(raw_ports: list[Any]) -> list[PortSpec]:
    return [
        PortSpec(
            name=item["name"],
            type=item.get("type", "string"),
            required=item.get("required", True),
            description=item.get("description", ""),
            expose=item.get("expose", True),
        )
        for item in raw_ports
    ]


def _load_pipeline_spec(ref: str) -> PipelineSpec:
    candidate = Path(ref)
    if candidate.exists():
        payload = StructuredLoader().load(candidate)
        raw = payload.get("pipeline_spec", payload)
        return PipelineSpec(
            name=raw["name"],
            version=raw.get("version", "1.0"),
            description=raw.get("description", ""),
            inputs=_dict_to_port_specs(raw.get("inputs", [])),
            outputs=_dict_to_port_specs(raw.get("outputs", [])),
            nodes=[],
            edges=[],
            metadata=raw.get("metadata", {}),
        )
    pipeline = create_pipeline(ref)
    return PipelineCompiler().compile(pipeline)


def _load_env_profile(ref: Any) -> EnvProfile:
    if not ref or ref == "local_default":
        return EnvProfile.local_default()
    if isinstance(ref, dict):
        return EnvProfile.from_dict(ref)
    return EnvProfileLoader().load(ref)


def _latest_run_dir(output_root: Path, before: set[Path]) -> Path | None:
    after = {path for path in output_root.iterdir() if path.is_dir()} if output_root.exists() else set()
    created = sorted(after - before)
    return created[-1] if created else None


def _load_failed_step_result(run_dir: Path) -> dict[str, Any] | None:
    steps_dir = run_dir / "steps"
    if not steps_dir.exists():
        return None
    for step_dir in sorted(steps_dir.iterdir(), reverse=True):
        result_file = step_dir / "result.json"
        if not result_file.exists():
            continue
        payload = json.loads(result_file.read_text(encoding="utf-8"))
        if payload.get("status") == "failed":
            return payload
    return None


class SkillRunner:
    """Execute structured skill handlers against template input."""

    def run(self, skill_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        get_skill(skill_name)
        handlers = {
            "test-op-generator": self._run_test_op_generator,
            "pipeline-generator": self._run_pipeline_generator,
            "case-generator": self._run_case_generator,
            "case-checker": self._run_case_checker,
            "case-runner": self._run_case_runner,
            "result-analyzer": self._run_result_analyzer,
        }
        if skill_name not in handlers:
            raise ValueError(f"no runtime handler implemented for skill: {skill_name}")
        return handlers[skill_name](payload)

    def _run_test_op_generator(self, payload: dict[str, Any]) -> dict[str, Any]:
        op_name = payload["op_name"]
        class_name = f"{_class_case(op_name)}Op"
        op_folder = payload.get("op_folder", payload.get("op_category", "custom"))
        inputs = _normalize_ports(payload.get("inputs", []), default_type="string")
        outputs = _normalize_ports(payload.get("outputs", []), default_type="string")
        attributes = payload.get("attributes", [])
        op_spec = {
            "name": op_name,
            "version": "1.0",
            "folder": op_folder,
            "description": payload.get("business_goal", ""),
            "inputs": inputs,
            "outputs": outputs,
            "attrs": attributes,
        }
        python_op_draft = "\n".join(
            [
                "@register_op",
                f"class {class_name}(TestOp):",
                '    """Generated from test-op template."""',
                "",
                "    spec = OpSpec(",
                '        version="1.0",',
                f"        description={payload.get('business_goal', '')!r},",
                "        inputs=[",
                *[
                    f"            PortSpec(name={item['name']!r}, type={item.get('type', 'string')!r}, description={item.get('description', '')!r}),"
                    for item in inputs
                ],
                "        ],",
                "        outputs=[",
                *[
                    f"            PortSpec(name={item['name']!r}, type={item.get('type', 'string')!r}, description={item.get('description', '')!r}),"
                    for item in outputs
                ],
                "        ],",
                f"        attrs={json.dumps(attributes, ensure_ascii=False, indent=8)},",
                "    )",
                "",
                "    def execute(self, step_context) -> dict[str, object]:",
                "        raise NotImplementedError('fill in business logic here')",
            ]
        )
        unit_test_draft = "\n".join(
            [
                f"class {class_name}Test(unittest.TestCase):",
                f"    def test_{_snake_case(op_name)}_returns_expected_outputs(self) -> None:",
                "        self.fail('implement op execution assertions')",
            ]
        )
        doc_draft = "\n".join(
            [
                f"# {op_name}",
                "",
                payload.get("business_goal", ""),
                "",
                "## Inputs",
                *(f"- `{item['name']}`: {item.get('type', 'string')}" for item in inputs),
                "",
                "## Outputs",
                *(f"- `{item['name']}`: {item.get('type', 'string')}" for item in outputs),
            ]
        )
        result = {
            "op_spec": op_spec,
            "python_op_draft": python_op_draft,
            "unit_test_draft": unit_test_draft,
            "doc_draft": doc_draft,
        }
        return _apply_test_op_scaffold(payload, result)

    def _run_pipeline_generator(self, payload: dict[str, Any]) -> dict[str, Any]:
        stages = payload.get("stages", [])
        stage_names = [item["name"] for item in stages if item.get("name")]
        required_ops = payload.get("required_ops", [])
        pipeline_inputs = _normalize_ports(payload.get("pipeline_inputs", []), default_type="string")
        pipeline_outputs = _normalize_ports(payload.get("pipeline_outputs", []), default_type="string")
        nodes: list[dict[str, Any]] = []
        for index, op_name in enumerate(required_ops, start=1):
            stage_name = stage_names[min(index - 1, len(stage_names) - 1)] if stage_names else None
            nodes.append(
                {
                    "name": f"{index:02d}_{_snake_case(op_name)}",
                    "op": op_name,
                    "group": stage_name,
                    "attrs": {},
                }
            )

        mermaid_lines = ["flowchart LR"]
        if stage_names:
            for stage_name in stage_names:
                mermaid_lines.append(f"  subgraph {stage_name}[{stage_name}]")
                for node in [item for item in nodes if item["group"] == stage_name]:
                    mermaid_lines.append(f"    {node['name']}[{node['op']}]")
                mermaid_lines.append("  end")
        else:
            for node in nodes:
                mermaid_lines.append(f"  {node['name']}[{node['op']}]")
        for source, target in zip(nodes, nodes[1:]):
            mermaid_lines.append(f"  {source['name']} --> {target['name']}")

        dsl_lines = [
            "@register_pipeline",
            f"class {_class_case(payload['pipeline_name'])}(Pipeline):",
            "    def define(self) -> None:",
        ]
        if pipeline_inputs:
            rendered_inputs = ", ".join(
                f"PortSpec(name={item['name']!r}, type={item.get('type', 'string')!r}, description={item.get('description', '')!r})"
                for item in pipeline_inputs
            )
            dsl_lines.append(f"        self.set_inputs({rendered_inputs})")
        if pipeline_outputs:
            rendered_outputs = ", ".join(
                f"PortSpec(name={item['name']!r}, type={item.get('type', 'string')!r}, description={item.get('description', '')!r})"
                for item in pipeline_outputs
            )
            dsl_lines.append(f"        self.set_outputs({rendered_outputs})")
        node_handles: list[str] = []
        if stage_names:
            for stage_name in stage_names:
                dsl_lines.append(f"        self.use_group({stage_name!r})")
                for node in [item for item in nodes if item["group"] == stage_name]:
                    handle_name = f"{node['name']}_node"
                    dsl_lines.append(f"        {handle_name} = self.add_node({node['name']!r}, {_class_case(node['op'])}Op())")
                    node_handles.append(handle_name)
        else:
            for node in nodes:
                handle_name = f"{node['name']}_node"
                dsl_lines.append(f"        {handle_name} = self.add_node({node['name']!r}, {_class_case(node['op'])}Op())")
                node_handles.append(handle_name)

        pipeline_spec = {
            "name": payload["pipeline_name"],
            "version": "1.0",
            "description": payload.get("business_goal", ""),
            "inputs": pipeline_inputs,
            "outputs": pipeline_outputs,
            "nodes": nodes,
            "edges": [
                {
                    "source_node": source["name"],
                    "source_port": "result",
                    "target_node": target["name"],
                    "target_port": "input",
                }
                for source, target in zip(nodes, nodes[1:])
            ],
            "metadata": {
                "groups": stage_names,
                "required_ops": required_ops,
                "optional_ops": payload.get("optional_ops", []),
                "data_flow_notes": payload.get("data_flow_notes", []),
            },
        }
        result = {
            "pipeline_spec": pipeline_spec,
            "python_pipeline_draft": "\n".join(dsl_lines),
            "mermaid_graph": "\n".join(mermaid_lines),
        }
        return _apply_pipeline_scaffold(payload, result)

    def _run_case_generator(self, payload: dict[str, Any]) -> dict[str, Any]:
        case_name = payload["case_name"]
        case_spec = CaseSpec(
            case_id=_snake_case(case_name),
            name=case_name,
            pipeline=payload["target_pipeline"],
            inputs=payload.get("inputs", {}),
            expected=payload.get("expected", {}),
            tags=payload.get("tags", []),
            priority=payload.get("priority", "P2"),
            metadata={
                "test_goal": payload.get("test_goal", ""),
                "environment_hint": payload.get("environment_hint", ""),
            },
        )
        return {
            "case_spec": case_spec.to_dict(),
            "yaml_case_draft": _render_yaml({"test_case": case_spec.to_dict()}),
        }

    def _run_case_checker(self, payload: dict[str, Any]) -> dict[str, Any]:
        case_spec = _load_case_from_payload(payload)
        pipeline_ref = payload.get("pipeline_spec_ref") or case_spec.pipeline
        report = CaseChecker().check(case_spec, _load_pipeline_spec(str(pipeline_ref)))
        return report.to_dict()

    def _run_case_runner(self, payload: dict[str, Any]) -> dict[str, Any]:
        case_ref = payload["case_ref"]
        output_root = Path(payload.get("output_dir") or "runs")
        debug = bool(payload.get("debug", False))
        execute = bool(payload.get("execute", False))
        env_profile_ref = payload.get("env_profile")
        env_profile = _load_env_profile(env_profile_ref)
        case = TestCaseLoader().load(case_ref)
        pipeline = create_pipeline(payload.get("pipeline_ref") or case.pipeline)
        pipeline_spec = PipelineCompiler().compile(pipeline)
        command = (
            f"testpipe run {case_ref}"
            f"{'' if output_root == Path('runs') else f' --output-root {output_root}'}"
            f"{'' if not env_profile_ref else f' --env-profile {env_profile_ref}'}"
            f"{' --debug' if debug else ''}"
        )

        result_location = None
        summary = None
        execution_console_log = None
        if execute:
            before = {path for path in output_root.iterdir() if path.is_dir()} if output_root.exists() else set()
            console_buffer = StringIO()
            with redirect_stdout(console_buffer):
                summary_obj = TestEngine(output_root=output_root, debug=debug).execute(
                    case_spec=case,
                    pipeline_spec=pipeline_spec,
                    env_profile=env_profile,
                )
            summary = summary_obj.to_dict()
            execution_console_log = console_buffer.getvalue().strip() or None
            run_dir = _latest_run_dir(output_root, before)
            result_location = None if run_dir is None else str(run_dir)

        return {
            "run_command": command,
            "run_plan_summary": {
                "case_id": case.case_id,
                "pipeline": pipeline_spec.name,
                "total_steps": len(pipeline_spec.nodes),
                "groups": list(dict.fromkeys(pipeline_spec.metadata.get("groups", []))),
                "output_root": str(output_root),
                "debug": debug,
                "execute": execute,
                "env_profile": env_profile.to_dict(),
            },
            "result_location": result_location,
            "summary": summary,
            "execution_console_log": execution_console_log,
        }

    def _run_result_analyzer(self, payload: dict[str, Any]) -> dict[str, Any]:
        summary_ref = Path(payload["summary_ref"])
        summary = json.loads(summary_ref.read_text(encoding="utf-8"))
        run_dir = summary_ref.parent
        internal_summary_ref = run_dir / "summary.internal.json"
        internal_summary = (
            json.loads(internal_summary_ref.read_text(encoding="utf-8"))
            if internal_summary_ref.exists()
            else summary
        )
        execution_log = run_dir / "execution.log"
        log_lines = execution_log.read_text(encoding="utf-8").splitlines() if execution_log.exists() else []
        failed_lines = [line for line in log_lines if "FAIL" in line or "error:" in line]
        failed_step_result = _load_failed_step_result(run_dir)
        failed_step = None if failed_step_result is None else failed_step_result.get("step_name")
        issues = list(internal_summary.get("issues", []))
        if not issues and failed_step_result is not None and failed_step_result.get("error"):
            issues = [str(failed_step_result.get("error", ""))]

        if summary["status"] == "passed":
            root_cause = "no failure detected"
            retryability = "not_needed"
            fix_suggestions: list[str] = []
        else:
            root_cause = issues[0] if issues else (failed_lines[-1] if failed_lines else "unknown failure")
            lowered = root_cause.lower()
            if "not found" in lowered or "missing" in lowered:
                retryability = "retry_after_fixing_input_or_artifact"
                fix_suggestions = ["检查输入路径、前置产物和步骤间输出路径是否正确"]
            elif "expected" in lowered:
                retryability = "retry_after_fixing_logic_or_expectation"
                fix_suggestions = ["检查 expected 断言、上游算子输出和业务基线是否一致"]
            else:
                retryability = "retry_after_fix"
                fix_suggestions = ["先根据 failed_step 和 execution.log 修复根因，再重试执行"]

        analysis_report = {
            "case_id": summary.get("case_id"),
            "pipeline": summary.get("pipeline"),
            "status": summary.get("status"),
            "failed_step": failed_step,
            "root_cause": root_cause,
            "retryability": retryability,
            "fix_suggestions": fix_suggestions,
            "evidence": {
                "issues": issues,
                "failed_log_lines": failed_lines[-5:],
                "summary_ref": str(summary_ref),
            },
        }
        return {
            "analysis_report": analysis_report,
            "root_cause": root_cause,
            "fix_suggestions": fix_suggestions,
        }
