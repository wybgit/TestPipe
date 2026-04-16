#!/usr/bin/env python3
"""Generate a minimal Pipeline scaffold from a YAML request."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from pprint import pformat
from typing import Any

import yaml


def snake_case(value: str) -> str:
    normalized = re.sub(r"[\-\s/]+", "_", value)
    normalized = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", normalized)
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", normalized)
    return re.sub(r"_+", "_", normalized).strip("_").lower()


def class_case(value: str) -> str:
    tokens = re.split(r"[^0-9A-Za-z]+", value)
    return "".join(token[:1].upper() + token[1:] for token in tokens if token)


def py_literal(value: Any) -> str:
    return pformat(value, width=100, sort_dicts=False)


def load_request(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("request file must contain a mapping")
    return payload


def ensure_package(root: Path, package_path: str) -> Path:
    current = root
    for token in package_path.split("/"):
        current = current / token
        current.mkdir(parents=True, exist_ok=True)
        init_file = current / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Generated package."""\n', encoding="utf-8")
    return current


def render_imports(nodes: list[dict[str, Any]]) -> list[str]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        import_path = str(node["import_path"])
        op_class = str(node["op_class"])
        if op_class not in grouped[import_path]:
            grouped[import_path].append(op_class)
    lines: list[str] = []
    for import_path in sorted(grouped):
        classes = ", ".join(sorted(grouped[import_path]))
        lines.append(f"from {import_path} import {classes}")
    return lines


def port_literal(item: dict[str, Any]) -> str:
    return (
        f'PortSpec(name={item["name"]!r}, type={item["type"]!r}, '
        f'required={item.get("required", True)!r}, description={item.get("description", "")!r})'
    )


def binding_literal(binding: str, handles: dict[str, str]) -> str:
    if binding.startswith("$pipeline."):
        return f'self.input_ref({binding.split(".", 1)[1]!r})'
    if "." not in binding:
        raise ValueError(f"unsupported binding syntax: {binding}")
    node_name, output_name = binding.split(".", 1)
    if node_name not in handles:
        raise ValueError(f"binding refers to unknown node: {binding}")
    return f'{handles[node_name]}.output({output_name!r})'


def render_pipeline_module(request: dict[str, Any]) -> str:
    pipeline_name = str(request["pipeline_name"])
    class_name = class_case(pipeline_name)
    nodes = request.get("nodes", [])
    handles: dict[str, str] = {node["name"]: snake_case(str(node["name"])) for node in nodes}
    imports = render_imports(nodes)

    lines = [
        '"""Generated Pipeline scaffold."""',
        "",
        "from __future__ import annotations",
        "",
        "from testpipe.core import Pipeline, register_pipeline",
        "from testpipe.spec import PortSpec",
    ]
    lines.extend(imports)
    lines.extend(
        [
            "",
            "",
            "@register_pipeline",
            f"class {class_name}(Pipeline):",
            f'    """{request.get("description", "").strip() or "Generated Pipeline scaffold."}"""',
            "",
            "    def define(self) -> None:",
        ]
    )
    pipeline_inputs = request.get("pipeline_inputs", [])
    if not pipeline_inputs:
        lines.append("        # TODO: define pipeline inputs when needed.")
    for item in pipeline_inputs:
        lines.append(
            "        self.add_input("
            f"{item['name']!r}, {item['type']!r}, required={item.get('required', True)!r}, "
            f"description={item.get('description', '')!r})"
        )

    previous_stage: str | None = None
    for node in nodes:
        stage = node.get("stage")
        if stage != previous_stage:
            lines.append("")
            lines.append(f"        self.set_stage({stage!r})")
            previous_stage = stage
        constructor_args = py_literal(node.get("constructor_args", {}))
        binding_items = []
        for input_name, binding in (node.get("inputs") or {}).items():
            binding_items.append(f"{input_name!r}: {binding_literal(str(binding), handles)}")
        if binding_items:
            inputs_literal = "{\n                " + ",\n                ".join(binding_items) + "\n            }"
        else:
            inputs_literal = "{}"
        lines.extend(
            [
                f"        {handles[node['name']]} = self.add_node(",
                f"            {node['name']!r},",
                f"            {node['op_class']}(**{constructor_args}),",
                f"            inputs={inputs_literal},",
                "        )",
            ]
        )

    pipeline_outputs = request.get("pipeline_outputs", [])
    if pipeline_outputs:
        lines.append("")
    for item in pipeline_outputs:
        source = binding_literal(str(item["source"]), handles)
        lines.append(
            "        self.add_output("
            f"{item['name']!r}, {source}, type={item['type']!r}, "
            f"required={item.get('required', True)!r}, description={item.get('description', '')!r})"
        )
    return "\n".join(lines) + "\n"


def render_testcase_yaml(request: dict[str, Any]) -> str:
    pipeline_name = str(request["pipeline_name"])
    pipeline_defaults = (
        request.get("case_defaults", {}).get("pipeline_level_overrides", {})
        if isinstance(request.get("case_defaults"), dict)
        else {}
    )
    case_defaults = request.get("case_defaults", {}).get("case", {})
    document = {
        "pipeline": {
            "name": pipeline_name,
            **pipeline_defaults,
        },
        "cases": [
            {
                "case_id": case_defaults.get("case_id", f"{snake_case(pipeline_name)}_case"),
                "description": case_defaults.get("description", "generated testcase scaffold"),
                "level": case_defaults.get("level", "P2"),
            }
        ],
    }
    return yaml.safe_dump(document, allow_unicode=True, sort_keys=False)


def render_test_module(request: dict[str, Any], import_path: str) -> str:
    class_name = class_case(str(request["pipeline_name"]))
    node_count = len(request.get("nodes", []))
    output_names = [item["name"] for item in request.get("pipeline_outputs", [])]
    lines = [
        '"""Compilation smoke tests for the generated Pipeline scaffold."""',
        "",
        "from __future__ import annotations",
        "",
        "import unittest",
        "",
        "from testpipe.core import PipelineCompiler",
        f"from {import_path} import {class_name}",
        "",
        "",
        f"class {class_name}CompileTest(unittest.TestCase):",
        "    def test_pipeline_compiles(self) -> None:",
        f"        spec = PipelineCompiler().compile({class_name}())",
        f"        self.assertEqual(spec.name, {class_name!r})",
        f"        self.assertEqual(len(spec.nodes), {node_count})",
        f"        self.assertEqual([item.name for item in spec.outputs], {output_names!r})",
        "",
        "",
        "if __name__ == '__main__':",
        "    unittest.main()",
    ]
    return "\n".join(lines) + "\n"


def render_doc(request: dict[str, Any], pipeline_module: str, testcase_file: str) -> str:
    lines = [
        f"# {request['pipeline_name']}",
        "",
        f"- Module: `{pipeline_module}`",
        f"- Example testcase: `{testcase_file}`",
        "",
        "## Description",
        "",
        request.get("description", "").strip() or "Generated Pipeline scaffold.",
        "",
        "## Node Order",
        "",
    ]
    for node in request.get("nodes", []):
        lines.append(f"- `{node['name']}`: `{node['op_class']}` in stage `{node.get('stage')}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, help="YAML request file")
    parser.add_argument("--output-root", default=".", help="Target repository root")
    args = parser.parse_args()

    request = load_request(Path(args.request))
    module_group = str(request.get("module_group", "custom")).replace(".", "/").strip("/")
    module_name = str(request.get("module_name") or snake_case(str(request["pipeline_name"])))
    class_name = class_case(str(request["pipeline_name"]))

    root = Path(args.output_root).resolve()
    pipelines_dir = ensure_package(root, "testpipe/pipelines")
    if module_group:
        pipelines_dir = ensure_package(pipelines_dir, module_group)
    tests_dir = root / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    testcase_dir = root / "examples" / "testcases"
    testcase_dir.mkdir(parents=True, exist_ok=True)
    docs_dir = root / "docs" / "guides" / "generated"
    docs_dir.mkdir(parents=True, exist_ok=True)

    pipeline_file = pipelines_dir / f"{module_name}.py"
    import_path = ".".join(part for part in ["testpipe", "pipelines", *([token for token in module_group.split("/") if token]), module_name] if part)
    test_file = tests_dir / f"test_{module_name}_pipeline.py"
    testcase_file = testcase_dir / f"{module_name}.yaml"
    doc_file = docs_dir / f"{module_name}_pipeline.md"

    pipeline_file.write_text(render_pipeline_module(request), encoding="utf-8")
    test_file.write_text(render_test_module(request, import_path), encoding="utf-8")
    testcase_file.write_text(render_testcase_yaml(request), encoding="utf-8")
    doc_file.write_text(render_doc(request, import_path, str(testcase_file.relative_to(root))), encoding="utf-8")

    payload = {
        "class_name": class_name,
        "written_files": [
            str(pipeline_file.relative_to(root)),
            str(test_file.relative_to(root)),
            str(testcase_file.relative_to(root)),
            str(doc_file.relative_to(root)),
        ],
        "manual_steps": [
            "Review node bindings and constructor_args before using the scaffold in production.",
            "If bootstrap import coverage is needed, update testpipe/pipelines/__init__.py or ensure callers import the module directly.",
            "Run python -m unittest discover -s tests -v and testpipe check-case on the generated testcase when the pipeline is ready.",
        ],
        "request_snapshot": py_literal(request),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
