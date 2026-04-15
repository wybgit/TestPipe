#!/usr/bin/env python3
"""Generate Markdown API docs for built-in ops and pipelines."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

from testpipe import bootstrap
from testpipe.core import PipelineCompiler, create_pipeline
from testpipe.core.registry import _OPS, _PIPELINES, get_op_group


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_API_DIR = REPO_ROOT / "docs" / "api"
OPS_DOC = DOCS_API_DIR / "ops_catalog.md"
PIPELINES_DOC = DOCS_API_DIR / "pipelines_catalog.md"


def main() -> None:
    bootstrap()
    DOCS_API_DIR.mkdir(parents=True, exist_ok=True)
    OPS_DOC.write_text(_render_ops_doc(), encoding="utf-8")
    PIPELINES_DOC.write_text(_render_pipelines_doc(), encoding="utf-8")


def _render_ops_doc() -> str:
    lines = [
        "# 内置算子 API",
        "",
        "本文档由 `scripts/generate_api_docs.py` 基于当前注册表自动生成。",
        "",
        f"当前内置算子数量：`{len(_OPS)}`",
        "",
    ]
    for op_name in sorted(_OPS):
        op_class = _OPS[op_name]
        spec = op_class.spec
        source_file = _source_path(op_class)
        group = get_op_group(op_class) or "builtin"
        lines.extend(
            [
                f"## {op_name}",
                "",
                f"- 类名：`{op_class.__name__}`",
                f"- 分组：`{group}`",
                f"- 版本：`{spec.version}`",
                f"- 源码：`{source_file}`",
                "",
                spec.description or "无描述。",
                "",
                "### Inputs",
                "",
                _ports_table(spec.inputs),
                "",
                "### Outputs",
                "",
                _ports_table(spec.outputs),
                "",
                "### Attrs",
                "",
                _attrs_table(spec.attrs),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _render_pipelines_doc() -> str:
    compiler = PipelineCompiler()
    lines = [
        "# 内置 Pipeline API",
        "",
        "本文档由 `scripts/generate_api_docs.py` 基于当前注册表自动生成。",
        "",
        f"当前内置 Pipeline 数量：`{len(_PIPELINES)}`",
        "",
    ]
    for pipeline_name in sorted(_PIPELINES):
        pipeline_class = _PIPELINES[pipeline_name]
        pipeline = create_pipeline(pipeline_name)
        spec = compiler.compile(pipeline)
        source_file = _source_path(pipeline_class)
        lines.extend(
            [
                f"## {pipeline_name}",
                "",
                f"- 类名：`{pipeline_class.__name__}`",
                f"- 版本：`{spec.version}`",
                f"- 源码：`{source_file}`",
                "",
                (spec.description or "无描述。"),
                "",
                "### Inputs",
                "",
                _ports_table(spec.inputs),
                "",
                "### Outputs",
                "",
                _ports_table(spec.outputs),
                "",
                "### Nodes",
                "",
            ]
        )

        for node in spec.nodes:
            lines.extend(
                [
                    f"#### {node.name}",
                    "",
                    f"- `op_name`: `{node.op_name}`",
                    f"- `stage`: `{node.stage or '-'}`",
                    f"- `attrs`: `{_inline_json(node.attrs)}`",
                    "",
                    "输入绑定：",
                    "",
                ]
            )
            if node.input_bindings:
                for binding in node.input_bindings:
                    source = (
                        f"pipeline.{binding.source_name}"
                        if binding.source_type == "pipeline_input"
                        else f"{binding.source_name}.{binding.source_port}"
                    )
                    lines.append(f"- `{binding.target_port}` <- `{source}`")
            else:
                lines.append("- 无")
            lines.extend(["", ""])

        lines.extend(
            [
                "### Output Bindings",
                "",
            ]
        )
        if spec.output_bindings:
            for binding in spec.output_bindings:
                source = (
                    f"pipeline.{binding.source_name}"
                    if binding.source_type == "pipeline_input"
                    else f"{binding.source_name}.{binding.source_port}"
                )
                lines.append(f"- `{binding.output_name}` <- `{source}`")
        else:
            lines.append("- 无")
        lines.extend(["", ""])
    return "\n".join(lines).rstrip() + "\n"


def _ports_table(items: list[Any]) -> str:
    if not items:
        return "| Name | Type | Required | Expose | Default | Description |\n| --- | --- | --- | --- | --- | --- |\n| - | - | - | - | - | 无 |"
    lines = [
        "| Name | Type | Required | Expose | Default | Description |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in items:
        lines.append(
            "| {name} | {type} | {required} | {expose} | {default} | {description} |".format(
                name=_escape_cell(item.name),
                type=_escape_cell(item.type),
                required="yes" if item.required else "no",
                expose="yes" if getattr(item, "expose", True) else "no",
                default=_escape_cell(_render_default(getattr(item, "default", None))),
                description=_escape_cell(item.description or "-"),
            )
        )
    return "\n".join(lines)


def _attrs_table(items: list[Any]) -> str:
    if not items:
        return "| Name | Type | Required | Default | Enum | Description |\n| --- | --- | --- | --- | --- | --- |\n| - | - | - | - | - | 无 |"
    lines = [
        "| Name | Type | Required | Default | Enum | Description |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in items:
        enum_value = "-" if item.enum is None else json.dumps(item.enum, ensure_ascii=False)
        lines.append(
            "| {name} | {type} | {required} | {default} | {enum} | {description} |".format(
                name=_escape_cell(item.name),
                type=_escape_cell(item.type),
                required="yes" if item.required else "no",
                default=_escape_cell(_render_default(item.default)),
                enum=_escape_cell(enum_value),
                description=_escape_cell(item.description or "-"),
            )
        )
    return "\n".join(lines)


def _render_default(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _inline_json(value: Any) -> str:
    if not value:
        return "-"
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _source_path(obj: Any) -> str:
    source = inspect.getsourcefile(obj)
    if source is None:
        return "-"
    return str(Path(source).resolve().relative_to(REPO_ROOT))


def _escape_cell(value: str) -> str:
    return value.replace("\n", "<br>").replace("|", "\\|")


if __name__ == "__main__":
    main()
