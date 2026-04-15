"""Runtime handlers for built-in skills."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any

import yaml

from testpipe.core import PipelineCompiler, create_pipeline, get_op_class
from testpipe.engine import TestEngine
from testpipe.loaders import EnvProfileLoader, FrameworkConfigLoader, StructuredLoader, TestCaseLoader
from testpipe.skills.registry import get_skill
from testpipe.spec import (
    CaseSpec,
    EdgeSpec,
    EnvProfile,
    InputBindingSpec,
    NodeSpec,
    OutputBindingSpec,
    PipelineSpec,
    PortSpec,
)
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
    module_name = _snake_case(result["op_spec"]["op_name"])
    root_dir = Path(str(scaffold["root_dir"]))
    op_dir = root_dir / str(scaffold.get("ops_dir", "ops"))
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


def _aggregate_reports(reports: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    statuses = [report["status"] for _, report in reports]
    status = "fail" if "fail" in statuses else "warn" if "warn" in statuses else "pass"
    return {
        "status": status,
        "case_count": len(reports),
        "cases": [
            {
                "case_id": case_id,
                **report,
            }
            for case_id, report in reports
        ],
    }


def _load_cases_from_payload(payload: dict[str, Any]) -> list[CaseSpec]:
    loader = TestCaseLoader()
    case_id = payload.get("case_id")
    if payload.get("case_ref"):
        if case_id is not None:
            return [loader.load(payload["case_ref"], case_id=case_id)]
        return loader.load_many(payload["case_ref"])
    if payload.get("case_spec"):
        raw = payload["case_spec"]
        if isinstance(raw, dict) and ("pipeline" in raw and "cases" in raw):
            document = raw
        elif isinstance(raw, dict) and ("testcases" in raw or "test_case" in raw or "test_suite" in raw):
            document = raw
        else:
            document = {"test_case": raw}
        if case_id is not None:
            return [loader.load_data(document, source="<inline>", case_id=case_id)]
        return loader.load_many_data(document, source="<inline>")
    raise ValueError("case_ref or case_spec is required")


def _dict_to_port_specs(raw_ports: list[Any]) -> list[PortSpec]:
    return [
        PortSpec(
            name=item["name"],
            type=item.get("type", "string"),
            required=item.get("required", True),
            description=item.get("description", ""),
        )
        for item in raw_ports
    ]


def _infer_case_node_inputs(pipeline_name: str, flat_inputs: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not flat_inputs:
        return {}
    pipeline_spec = PipelineCompiler().compile(create_pipeline(pipeline_name))
    edge_targets: dict[str, set[str]] = {}
    for node in pipeline_spec.nodes:
        for binding in node.input_bindings:
            edge_targets.setdefault(node.name, set()).add(binding.target_port)

    inferred: dict[str, dict[str, Any]] = {}
    for input_name, value in flat_inputs.items():
        candidates: list[str] = []
        for node in pipeline_spec.nodes:
            op_inputs = {item.name for item in get_op_class(node.op_name).spec.inputs}
            if input_name not in op_inputs:
                continue
            if input_name in edge_targets.get(node.name, set()):
                continue
            candidates.append(node.name)
        if len(candidates) != 1:
            continue
        inferred.setdefault(candidates[0], {})[input_name] = value
    return inferred


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
            nodes=[
                NodeSpec(
                    name=item["name"],
                    op_name=item.get("op_name", item.get("op_type", "")),
                    op_version=item.get("op_version"),
                    stage=item.get("stage"),
                    attrs=item.get("attrs", {}),
                    input_bindings=[InputBindingSpec(**binding) for binding in item.get("input_bindings", [])],
                )
                for item in raw.get("nodes", [])
            ],
            edges=[EdgeSpec(**item) for item in raw.get("edges", [])],
            output_bindings=[OutputBindingSpec(**item) for item in raw.get("output_bindings", [])],
            metadata=raw.get("metadata", {}),
        )
    pipeline = create_pipeline(ref)
    return PipelineCompiler().compile(pipeline)


def _load_env_profile(ref: Any, *, config_ref: Any = None) -> EnvProfile:
    config_loader = FrameworkConfigLoader()
    framework_config = config_loader.load(config_ref) if config_ref else config_loader.load_default()
    if not ref or ref in {"local_default", "local"}:
        return framework_config.resolve_env_profile(None)
    if isinstance(ref, dict):
        return EnvProfile.from_dict(ref)
    candidate = Path(str(ref))
    if candidate.exists():
        return EnvProfileLoader().load(candidate)
    return framework_config.resolve_env_profile(str(ref))


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
        inputs = _normalize_ports(payload.get("inputs", []), default_type="string")
        outputs = _normalize_ports(payload.get("outputs", []), default_type="string")
        attributes = payload.get("attributes", [])
        op_spec = {
            "op_name": op_name,
            "version": "1.0",
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
                    "op_name": op_name,
                    "stage": stage_name,
                    "attrs": {},
                }
            )

        mermaid_lines = ["flowchart LR"]
        if stage_names:
            for stage_name in stage_names:
                mermaid_lines.append(f"  subgraph {stage_name}[{stage_name}]")
                for node in [item for item in nodes if item["stage"] == stage_name]:
                    mermaid_lines.append(f"    {node['name']}[{node['op_name']}]")
                mermaid_lines.append("  end")
        else:
            for node in nodes:
                mermaid_lines.append(f"  {node['name']}[{node['op_name']}]")
        for source, target in zip(nodes, nodes[1:]):
            mermaid_lines.append(f"  {source['name']} --> {target['name']}")

        dsl_lines = [
            "@register_pipeline",
            f"class {_class_case(payload['pipeline_name'])}(Pipeline):",
            "    def define(self) -> None:",
        ]
        input_refs: list[tuple[dict[str, Any], str]] = []
        if pipeline_inputs:
            for item in pipeline_inputs:
                ref_name = _snake_case(item["name"])
                input_refs.append((item, ref_name))
                dsl_lines.append(
                    f"        {ref_name} = self.add_input({item['name']!r}, {item.get('type', 'string')!r}, description={item.get('description', '')!r})"
                )

        node_refs: list[tuple[dict[str, Any], str]] = []
        if stage_names:
            for stage_name in stage_names:
                dsl_lines.append(f"        self.set_stage({stage_name!r})")
                for node in [item for item in nodes if item["stage"] == stage_name]:
                    node_ref = _snake_case(node["name"])
                    node_refs.append((node, node_ref))
                    if not node_refs[:-1] and input_refs:
                        dsl_lines.append(
                            f"        {node_ref} = self.add_node({node['name']!r}, {_class_case(node['op_name'])}Op(), inputs={{'input': {input_refs[0][1]}}})"
                        )
                    elif len(node_refs) > 1:
                        previous_ref = node_refs[-2][1]
                        dsl_lines.append(
                            f"        {node_ref} = self.add_node({node['name']!r}, {_class_case(node['op_name'])}Op(), inputs={{'input': {previous_ref}.output('result')}})"
                        )
                    else:
                        dsl_lines.append(f"        {node_ref} = self.add_node({node['name']!r}, {_class_case(node['op_name'])}Op())")
        else:
            for node in nodes:
                node_ref = _snake_case(node["name"])
                node_refs.append((node, node_ref))
                if not node_refs[:-1] and input_refs:
                    dsl_lines.append(
                        f"        {node_ref} = self.add_node({node['name']!r}, {_class_case(node['op_name'])}Op(), inputs={{'input': {input_refs[0][1]}}})"
                    )
                elif len(node_refs) > 1:
                    previous_ref = node_refs[-2][1]
                    dsl_lines.append(
                        f"        {node_ref} = self.add_node({node['name']!r}, {_class_case(node['op_name'])}Op(), inputs={{'input': {previous_ref}.output('result')}})"
                    )
                else:
                    dsl_lines.append(f"        {node_ref} = self.add_node({node['name']!r}, {_class_case(node['op_name'])}Op())")
        if pipeline_outputs and node_refs:
            last_ref = node_refs[-1][1]
            for item in pipeline_outputs:
                dsl_lines.append(
                    f"        self.add_output({item['name']!r}, {last_ref}.output('result'), type={item.get('type', 'string')!r}, description={item.get('description', '')!r})"
                )

        pipeline_spec = {
            "name": payload["pipeline_name"],
            "version": "1.0",
            "description": payload.get("business_goal", ""),
            "inputs": pipeline_inputs,
            "outputs": pipeline_outputs,
            "nodes": nodes,
            "output_bindings": [
                {
                    "output_name": item["name"],
                    "source_type": "node_output",
                    "source_name": nodes[-1]["name"],
                    "source_port": "result",
                }
                for item in pipeline_outputs
            ]
            if nodes
            else [],
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
                "stages": stage_names,
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
        if "pipeline" in payload and "cases" in payload:
            document = {
                "pipeline": deepcopy(payload["pipeline"]),
                "cases": deepcopy(payload["cases"]),
            }
            cases = TestCaseLoader().load_many_data(document, source="<generated>")
            result = {
                "yaml_case_draft": _render_yaml(document),
                "case_specs": [item.to_dict() for item in cases],
            }
            if len(cases) == 1:
                result["case_spec"] = cases[0].to_dict()
            return result

        case_name = payload["case_name"]
        case_id = _snake_case(case_name)
        target_pipeline = payload["target_pipeline"]
        case_spec = CaseSpec(
            case_id=case_id,
            pipeline=target_pipeline,
            inputs=payload.get("inputs", {}),
            expected=payload.get("expected", {}),
            tags=payload.get("tags", []),
            priority=payload.get("priority", "P2"),
            description=payload.get("test_goal", ""),
            metadata={
                "test_goal": payload.get("test_goal", ""),
                "environment_hint": payload.get("environment_hint", ""),
            },
        )
        return {
            "case_spec": case_spec.to_dict(),
            "yaml_case_draft": _render_yaml(
                {
                    "pipeline": {
                        "name": target_pipeline,
                    },
                    "cases": [
                        {
                            "case_id": case_spec.case_id,
                            **({"description": case_spec.description} if case_spec.description else {}),
                            **({"level": case_spec.priority} if case_spec.priority else {}),
                            **_infer_case_node_inputs(target_pipeline, case_spec.inputs),
                        }
                    ],
                }
            ),
        }

    def _run_case_checker(self, payload: dict[str, Any]) -> dict[str, Any]:
        reports: list[tuple[str, dict[str, Any]]] = []
        pipeline_specs: dict[str, PipelineSpec] = {}
        checker = CaseChecker()
        for case_spec in _load_cases_from_payload(payload):
            pipeline_ref = payload.get("pipeline_spec_ref") or case_spec.pipeline
            pipeline_spec = pipeline_specs.get(str(pipeline_ref))
            if pipeline_spec is None:
                pipeline_spec = _load_pipeline_spec(str(pipeline_ref))
                pipeline_specs[str(pipeline_ref)] = pipeline_spec
            reports.append((case_spec.case_id, checker.check(case_spec, pipeline_spec).to_dict()))
        return reports[0][1] if len(reports) == 1 else _aggregate_reports(reports)

    def _run_case_runner(self, payload: dict[str, Any]) -> dict[str, Any]:
        case_ref = payload["case_ref"]
        output_root = Path(payload.get("output_dir") or "runs")
        debug = bool(payload.get("debug", False))
        execute = bool(payload.get("execute", False))
        env_profile_ref = payload.get("env_profile")
        framework_config_ref = payload.get("framework_config")
        env_profile = _load_env_profile(env_profile_ref, config_ref=framework_config_ref)
        selected_case_id = payload.get("case_id")
        cases = TestCaseLoader().load_many(case_ref)
        if selected_case_id is not None:
            cases = [case for case in cases if case.case_id == selected_case_id]
            if not cases:
                raise ValueError(f"case_id not found in case file: {selected_case_id}")
        command = (
            f"testpipe run {case_ref}"
            f"{'' if not selected_case_id else f' --case-id {selected_case_id}'}"
            f"{'' if output_root == Path('runs') else f' --output-root {output_root}'}"
            f"{'' if not framework_config_ref else f' --config {framework_config_ref}'}"
            f"{'' if not env_profile_ref else f' --env-profile {env_profile_ref}'}"
            f"{' --debug' if debug else ''}"
        )

        result_location = None
        result_locations = None
        summary = None
        summaries = None
        execution_console_log = None
        pipeline_specs: dict[str, PipelineSpec] = {}
        if execute:
            before = {path for path in output_root.iterdir() if path.is_dir()} if output_root.exists() else set()
            console_buffer = StringIO()
            with redirect_stdout(console_buffer):
                engine = TestEngine(output_root=output_root, debug=debug)
                summary_objs = []
                for case in cases:
                    pipeline_spec = pipeline_specs.get(case.pipeline)
                    if pipeline_spec is None:
                        pipeline_spec = PipelineCompiler().compile(create_pipeline(payload.get("pipeline_ref") or case.pipeline))
                        pipeline_specs[case.pipeline] = pipeline_spec
                    summary_objs.append(
                        engine.execute(
                            case_spec=case,
                            pipeline_spec=pipeline_spec,
                            env_profile=env_profile,
                        )
                    )
            execution_console_log = console_buffer.getvalue().strip() or None
            created_runs = []
            if output_root.exists():
                created_runs = sorted(path for path in output_root.iterdir() if path.is_dir() and path not in before)
            result_locations = [{"case_id": item.case_id, "run_dir": str(path)} for item, path in zip(cases, created_runs, strict=False)]
            summaries = [item.to_dict() for item in summary_objs]
            if len(summary_objs) == 1:
                summary = summary_objs[0].to_dict()
                result_location = None if not created_runs else str(created_runs[-1])

        return {
            "run_command": command,
            "run_plan_summary": {
                "case_count": len(cases),
                "case_ids": [case.case_id for case in cases],
                "pipelines": sorted({case.pipeline for case in cases}),
                "output_root": str(output_root),
                "debug": debug,
                "execute": execute,
                "env_profile": env_profile.to_dict(),
            },
            "result_location": result_location,
            "result_locations": result_locations,
            "summary": summary,
            "summaries": summaries,
            "graph_files": None
            if result_location is None
            else {
                "dot_path": str(Path(result_location) / "pipeline_graph.dot"),
                "pdf_path": str(Path(result_location) / "pipeline_graph.pdf"),
            },
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
