#!/usr/bin/env python3
"""Generate a minimal TestOp scaffold from a YAML request."""

from __future__ import annotations

import argparse
import json
import re
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


def render_port(kind: str, item: dict[str, Any]) -> str:
    return (
        f'{kind}(name={item["name"]!r}, type={item["type"]!r}, '
        f'required={item.get("required", True)!r}, description={item.get("description", "")!r})'
    )


def render_attr(item: dict[str, Any]) -> str:
    base = [
        f'name={item["name"]!r}',
        f'type={item["type"]!r}',
        f'required={item.get("required", False)!r}',
        f'default={item.get("default")!r}',
        f'description={item.get("description", "")!r}',
    ]
    if "enum" in item:
        base.append(f'enum={item["enum"]!r}')
    return f"AttrSpec({', '.join(base)})"


def render_op_module(request: dict[str, Any]) -> str:
    op_name = str(request["op_name"])
    class_name = f"{class_case(op_name)}Op"
    inputs = request.get("inputs", [])
    outputs = request.get("outputs", [])
    attrs = request.get("attrs", [])
    behavior = request.get("behavior_summary", [])

    lines = [
        '"""Generated TestOp scaffold."""',
        "",
        "from __future__ import annotations",
        "",
        "from testpipe.core import TestOp, register_op",
        "from testpipe.spec import AttrSpec, OpSpec, PortSpec",
        "",
        "",
        "@register_op",
        f"class {class_name}(TestOp):",
        f'    """{request.get("description", "").strip() or "Generated TestOp scaffold."}"""',
        "",
        "    spec = OpSpec(",
        '        version="1.0",',
        f'        description={request.get("description", "").strip()!r},',
        "        inputs=[",
    ]
    for item in inputs:
        lines.append(f"            {render_port('PortSpec', item)},")
    lines.extend(
        [
            "        ],",
            "        outputs=[",
        ]
    )
    for item in outputs:
        lines.append(f"            {render_port('PortSpec', item)},")
    lines.extend(
        [
            "        ],",
            "        attrs=[",
        ]
    )
    for item in attrs:
        lines.append(f"            {render_attr(item)},")
    lines.extend(
        [
            "        ],",
            "    )",
            "",
            "    def execute(self, step_context):",
        ]
    )
    if behavior:
        for item in behavior:
            lines.append(f"        # TODO: {item}")
    else:
        lines.append("        # TODO: implement the business logic described by this op.")
    lines.extend(
        [
            "        raise NotImplementedError(",
            f'            "{class_name}.execute() must be implemented for the current task."',
            "        )",
        ]
    )
    return "\n".join(lines) + "\n"


def render_test_module(request: dict[str, Any], import_path: str) -> str:
    op_name = str(request["op_name"])
    class_name = f"{class_case(op_name)}Op"
    input_names = [item["name"] for item in request.get("inputs", [])]
    output_names = [item["name"] for item in request.get("outputs", [])]
    attr_names = [item["name"] for item in request.get("attrs", [])]

    lines = [
        '"""Contract tests for the generated TestOp scaffold."""',
        "",
        "from __future__ import annotations",
        "",
        "import unittest",
        "",
        f"from {import_path} import {class_name}",
        "",
        "",
        f"class {class_name}ContractTest(unittest.TestCase):",
        "    def test_spec_contract(self) -> None:",
        f"        self.assertEqual({class_name}.spec.version, '1.0')",
        f"        self.assertEqual([item.name for item in {class_name}.spec.inputs], {input_names!r})",
        f"        self.assertEqual([item.name for item in {class_name}.spec.outputs], {output_names!r})",
        f"        self.assertEqual([item.name for item in {class_name}.spec.attrs], {attr_names!r})",
        "",
        "",
        "if __name__ == '__main__':",
        "    unittest.main()",
    ]
    return "\n".join(lines) + "\n"


def render_doc(request: dict[str, Any], module_import: str, test_file: str) -> str:
    behavior = request.get("behavior_summary", [])
    expectations = request.get("test_expectations", [])
    lines = [
        f"# {request['op_name']}",
        "",
        f"- Module: `{module_import}`",
        f"- Test: `{test_file}`",
        "",
        "## Description",
        "",
        request.get("description", "").strip() or "Generated TestOp scaffold.",
        "",
        "## Behavior Summary",
        "",
    ]
    if behavior:
        lines.extend(f"- {item}" for item in behavior)
    else:
        lines.append("- TODO: describe the execution path.")
    lines.extend(["", "## Test Expectations", ""])
    if expectations:
        lines.extend(f"- {item}" for item in expectations)
    else:
        lines.append("- TODO: define the expected behaviors.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, help="YAML request file")
    parser.add_argument("--output-root", default=".", help="Target repository root")
    args = parser.parse_args()

    request = load_request(Path(args.request))
    module_group = str(request.get("module_group", "custom")).replace(".", "/").strip("/")
    module_name = str(request.get("module_name") or snake_case(str(request["op_name"])))
    class_name = f"{class_case(str(request['op_name']))}Op"

    root = Path(args.output_root).resolve()
    ops_dir = ensure_package(root, "testpipe/ops")
    if module_group:
        ops_dir = ensure_package(ops_dir, module_group)
    tests_dir = root / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    docs_dir = root / "docs" / "guides" / "generated"
    docs_dir.mkdir(parents=True, exist_ok=True)

    op_file = ops_dir / f"{module_name}.py"
    import_path = ".".join(part for part in ["testpipe", "ops", *([token for token in module_group.split("/") if token]), module_name] if part)
    test_file = tests_dir / f"test_{module_name}_op.py"
    doc_file = docs_dir / f"{module_name}_op.md"

    op_file.write_text(render_op_module(request), encoding="utf-8")
    test_file.write_text(render_test_module(request, import_path), encoding="utf-8")
    doc_file.write_text(render_doc(request, import_path, str(test_file.relative_to(root))), encoding="utf-8")

    payload = {
        "class_name": class_name,
        "written_files": [
            str(op_file.relative_to(root)),
            str(test_file.relative_to(root)),
            str(doc_file.relative_to(root)),
        ],
        "manual_steps": [
            "Implement execute() and replace the NotImplementedError placeholder.",
            "If bootstrap import coverage is needed, update testpipe/ops/__init__.py or import the module from a pipeline.",
            "Run python -m unittest discover -s tests -v and python scripts/generate_api_docs.py if public API docs changed.",
        ],
        "request_snapshot": py_literal(request),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
