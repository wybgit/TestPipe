"""Render PipelineSpec objects into DOT/PDF graphs."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from testpipe.core import get_op_class

_NODE_WIDTH = 3.4
_LABEL_WRAP_WIDTH = 34


def export_pipeline_graph(
    pipeline_spec,
    case_spec,
    output_dir: str | Path,
    *,
    basename: str = "pipeline_graph",
    node_outputs: dict[str, dict[str, Any]] | None = None,
    pipeline_outputs: dict[str, Any] | None = None,
    render_pdf: bool = True,
) -> dict[str, str | None]:
    """Export a pipeline graph to DOT and, by default, render a PDF."""

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    dot_path = output_root / f"{basename}.dot"
    pdf_path = output_root / f"{basename}.pdf"

    dot_text = _build_dot(
        pipeline_spec,
        case_spec,
        node_outputs=node_outputs or {},
        pipeline_outputs=pipeline_outputs or {},
    )
    dot_path.write_text(dot_text, encoding="utf-8")

    rendered_pdf: str | None = None
    if render_pdf and shutil.which("dot") is not None:
        subprocess.run(
            ["dot", "-Tpdf", str(dot_path), "-o", str(pdf_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        rendered_pdf = str(pdf_path)

    return {
        "dot_path": str(dot_path),
        "pdf_path": rendered_pdf,
    }


def _build_dot(pipeline_spec, case_spec, *, node_outputs: dict[str, dict[str, Any]], pipeline_outputs: dict[str, Any]) -> str:
    pipeline_input_values = _pipeline_input_values(pipeline_spec, case_spec)
    direct_node_inputs = _direct_node_inputs(pipeline_spec, case_spec)
    lines = [
        "digraph TestPipePipeline {",
        '  graph [',
        '    rankdir=TB,',
        '    splines=polyline,',
        '    nodesep=0.35,',
        '    ranksep=0.8,',
        '    pad=0.25,',
        '    bgcolor="#FFFFFF",',
        '    labelloc="t",',
        '    labeljust="l",',
        f'    label="{_graph_label(case_spec, pipeline_spec)}"',
      "  ];",
        f'  node [shape=box, style="filled", fontname="Helvetica", fontsize=11, margin="0.18,0.12", width={_NODE_WIDTH}, color="#94A3B8", penwidth=1.0];',
        '  edge [color="#64748B", penwidth=1.0, arrowsize=0.7];',
        "",
    ]

    resolved_inputs = _resolve_node_inputs(pipeline_spec, case_spec, node_outputs, pipeline_input_values)
    lines.extend(_render_input_nodes(pipeline_spec, pipeline_input_values, direct_node_inputs))
    lines.append("")

    lines.extend(_render_op_nodes(pipeline_spec, resolved_inputs, node_outputs))
    lines.append("")

    lines.extend(_render_output_nodes(pipeline_spec, pipeline_outputs))
    lines.append("")
    lines.extend(_render_edges(pipeline_spec, direct_node_inputs=direct_node_inputs, pipeline_input_values=pipeline_input_values))
    lines.append("}")
    return "\n".join(lines) + "\n"


def _graph_label(case_spec, pipeline_spec) -> str:
    return _escape_dot(f"Pipeline: {pipeline_spec.name}") + "\\n" + _escape_dot(f"Case: {case_spec.case_id}")


def _render_input_nodes(
    pipeline_spec,
    pipeline_input_values: dict[str, Any],
    direct_node_inputs: dict[str, dict[str, Any]],
) -> list[str]:
    lines = ["  // Inputs"]
    for item in pipeline_spec.inputs:
        value = pipeline_input_values.get(item.name, _MISSING)
        if value is _MISSING and not item.required:
            continue
        node_id = _input_node_id(item.name)
        lines.append(f"  {node_id} [{_node_attrs(_input_label(item.name, value), fill='#EAF4FF', color='#93C5FD')}] ;")
    for node in pipeline_spec.nodes:
        extra_inputs = direct_node_inputs.get(node.name, {})
        if not extra_inputs:
            continue
        lines.append(
            f"  {_param_input_node_id(node.name)} [{_node_attrs(_node_param_input_label(node.name, extra_inputs), fill='#EFF6FF', color='#BFDBFE')}] ;"
        )
    return lines


def _render_op_nodes(
    pipeline_spec,
    resolved_inputs: dict[str, dict[str, Any]],
    node_outputs: dict[str, dict[str, Any]],
) -> list[str]:
    lines = ["  // Nodes"]
    current_stage: str | None = None
    for node in pipeline_spec.nodes:
        if node.stage != current_stage:
            current_stage = node.stage
            if current_stage:
                lines.append(f"  // Stage: {current_stage}")
        lines.append(
            f"  {_op_node_id(node.name)} [{_node_attrs(_op_label(node, resolved_inputs.get(node.name, {}), node_outputs.get(node.name, {})), fill='#FFFFFF', color='#CBD5E1')}] ;"
        )
    return lines


def _render_output_nodes(pipeline_spec, pipeline_outputs: dict[str, Any]) -> list[str]:
    lines = ["  // Outputs"]
    for item in pipeline_spec.outputs:
        node_id = _output_node_id(item.name)
        value = pipeline_outputs.get(item.name, _MISSING)
        lines.append(f"  {node_id} [{_node_attrs(_output_label(item.name, value), fill='#ECFDF3', color='#86EFAC')}] ;")
    return lines


def _render_edges(
    pipeline_spec,
    *,
    direct_node_inputs: dict[str, dict[str, Any]],
    pipeline_input_values: dict[str, Any],
) -> list[str]:
    lines: list[str] = []
    pipeline_input_map = {item.name: item for item in pipeline_spec.inputs}
    for node in pipeline_spec.nodes:
        if direct_node_inputs.get(node.name):
            lines.append(f'  {_param_input_node_id(node.name)} -> {_op_node_id(node.name)} [color="#93C5FD"];')
    for node in pipeline_spec.nodes:
        for binding in node.input_bindings:
            target_id = _op_node_id(node.name)
            if binding.source_type == "pipeline_input":
                input_spec = pipeline_input_map.get(binding.source_name)
                if input_spec is not None and binding.source_name not in pipeline_input_values and not input_spec.required:
                    continue
                lines.append(f'  {_input_node_id(binding.source_name)} -> {target_id} [color="#60A5FA"];')
                continue
            if binding.source_type == "node_output":
                lines.append(f'  {_op_node_id(binding.source_name)} -> {target_id} [color="#6B7280"];')
    for binding in pipeline_spec.output_bindings:
        target_id = _output_node_id(binding.output_name)
        if binding.source_type == "pipeline_input":
            input_spec = pipeline_input_map.get(binding.source_name)
            if input_spec is not None and binding.source_name not in pipeline_input_values and not input_spec.required:
                continue
            lines.append(f'  {_input_node_id(binding.source_name)} -> {target_id} [color="#34D399"];')
            continue
        if binding.source_type == "node_output":
            lines.append(f'  {_op_node_id(binding.source_name)} -> {target_id} [color="#34D399"];')
    return lines


def _resolve_node_inputs(
    pipeline_spec,
    case_spec,
    node_outputs: dict[str, dict[str, Any]],
    pipeline_input_values: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    pipeline_input_map = {item.name: item for item in pipeline_spec.inputs}
    resolved: dict[str, dict[str, Any]] = {}
    for node in pipeline_spec.nodes:
        op_class = get_op_class(node.op_name)
        declared_ports = {item.name for item in op_class.spec.inputs}
        values: dict[str, Any] = {}
        bound_ports: set[str] = set()

        for binding in node.input_bindings:
            if binding.target_port not in declared_ports:
                continue
            bound_ports.add(binding.target_port)
            if binding.source_type == "pipeline_input":
                if binding.source_name in pipeline_input_values:
                    values[binding.target_port] = pipeline_input_values[binding.source_name]
                elif pipeline_input_map.get(binding.source_name) is None or pipeline_input_map[binding.source_name].required:
                    values[binding.target_port] = f"<pipeline:{binding.source_name}>"
                continue
            if binding.source_type == "node_output":
                upstream_outputs = node_outputs.get(binding.source_name, {})
                values[binding.target_port] = upstream_outputs.get(
                    binding.source_port,
                    f"<{binding.source_name}.{binding.source_port}>",
                )

        for key, value in case_spec.inputs_by_node.get(node.name, {}).items():
            if key in declared_ports and key not in bound_ports:
                values[key] = value

        for item in pipeline_spec.inputs:
            if item.name in bound_ports or item.name in values:
                continue
            if item.name in declared_ports and item.name in pipeline_input_values:
                values[item.name] = pipeline_input_values[item.name]

        resolved[node.name] = values
    return resolved


def _pipeline_input_values(pipeline_spec, case_spec) -> dict[str, Any]:
    values = dict(case_spec.inputs)
    pipeline_input_names = {item.name for item in pipeline_spec.inputs}
    for mapping in case_spec.inputs_by_node.values():
        for key, value in mapping.items():
            if key in pipeline_input_names and key not in values:
                values[key] = value
    return values


def _direct_node_inputs(pipeline_spec, case_spec) -> dict[str, dict[str, Any]]:
    pipeline_input_names = {item.name for item in pipeline_spec.inputs}
    direct_inputs: dict[str, dict[str, Any]] = {}
    for node in pipeline_spec.nodes:
        bound_ports = {binding.target_port for binding in node.input_bindings}
        values: dict[str, Any] = {}
        for key, value in case_spec.inputs_by_node.get(node.name, {}).items():
            if key in bound_ports or key in pipeline_input_names:
                continue
            values[key] = value
        if values:
            direct_inputs[node.name] = values
    return direct_inputs


def _input_label(name: str, value: Any) -> str:
    return _multiline_label(
        f"input: {name}",
        [
            ("value", value),
        ],
    )


def _node_param_input_label(node_name: str, values: dict[str, Any]) -> str:
    return _multiline_label(
        f"input: {node_name}",
        [
            ("value", values),
        ],
    )


def _op_label(node, inputs: dict[str, Any], outputs: dict[str, Any]) -> str:
    attr_values = _visible_node_attrs(node, inputs)
    sections: list[tuple[str, Any]] = []
    if inputs:
        sections.append(("inputs", inputs))
    if attr_values:
        sections.append(("attrs", attr_values))
    if outputs:
        sections.append(("outputs", outputs))
    return _multiline_label(
        node.name,
        sections,
        subtitle=f"op: {node.op_name}",
    )


def _output_label(name: str, value: Any) -> str:
    return _multiline_label(
        f"output: {name}",
        [
            ("value", value),
        ],
    )


def _multiline_label(
    header: str,
    sections: list[tuple[str, Any]],
    *,
    prefix: str | None = None,
    subtitle: str | None = None,
) -> str:
    lines = [header]
    if prefix:
        lines.insert(0, prefix)
    if subtitle:
        lines.append(subtitle)
    for title, payload in sections:
        if payload is _MISSING or payload in ({}, []):
            continue
        lines.append(f"{title}:")
        lines.extend(f"  {line}" for line in _format_block(payload))
    return _dot_multiline_text(lines)


def _format_block(value: Any) -> list[str]:
    if value is _MISSING:
        return ["<missing>"]
    if isinstance(value, dict):
        if not value:
            return ["{}"]
        lines: list[str] = []
        for key, item in value.items():
            child_lines = _format_block(item)
            if len(child_lines) == 1:
                lines.extend(_wrap_prefixed(f"{key}: ", child_lines[0]))
                continue
            lines.append(f"{key}:")
            lines.extend(f"  {line}" for line in child_lines)
        return lines
    if isinstance(value, (list, tuple)):
        if not value:
            return ["[]"]
        lines = []
        for item in value:
            child_lines = _format_block(item)
            if len(child_lines) == 1:
                lines.extend(_wrap_prefixed("- ", child_lines[0]))
                continue
            lines.append("-")
            lines.extend(f"  {line}" for line in child_lines)
        return lines
    return _wrap_text(str(value))


def _wrap_prefixed(prefix: str, text: str) -> list[str]:
    wrapped = _wrap_text(
        prefix + text,
        width=_LABEL_WRAP_WIDTH + len(prefix),
        subsequent_indent=" " * len(prefix),
    )
    return wrapped or [prefix.rstrip()]


def _wrap_text(text: str, *, width: int = _LABEL_WRAP_WIDTH, subsequent_indent: str = "") -> list[str]:
    lines: list[str] = []
    current = ""
    tokens = _segment_text(text)

    def flush() -> None:
        nonlocal current
        if current:
            lines.append(current.rstrip())
            current = subsequent_indent

    for token in tokens:
        if not current:
            current = subsequent_indent if lines and subsequent_indent else ""
        if len(current) + len(token) <= width:
            current += token
            continue
        if current.strip():
            flush()
        while len(current) + len(token) > width:
            available = max(width - len(current), 8)
            current += token[:available]
            token = token[available:]
            flush()
        current += token

    if current:
        lines.append(current.rstrip())
    return lines or [text]


def _segment_text(text: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    separators = {"/", "\\", "_", "-", ":", "?", "&", "=", ",", "."}
    for char in text:
        current.append(char)
        if char.isspace() or char in separators:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tokens


def _dot_multiline_text(lines: list[str]) -> str:
    escaped = "\\l".join(_escape_dot(line) for line in lines if line is not None)
    return f"{escaped}\\l"


def _visible_node_attrs(node, inputs: dict[str, Any]) -> dict[str, Any]:
    if not node.attrs:
        return {}
    op_class = get_op_class(node.op_name)
    input_names = {item.name for item in op_class.spec.inputs}
    return {
        key: value
        for key, value in node.attrs.items()
        if key not in input_names
    }


def _node_attrs(label: str, *, fill: str, color: str) -> str:
    return f'label="{label}", fillcolor="{fill}", color="{color}", width={_NODE_WIDTH}'


def _input_node_id(name: str) -> str:
    return f"in_{_safe_id(name)}"


def _param_input_node_id(node_name: str) -> str:
    return f"param_{_safe_id(node_name)}"


def _op_node_id(name: str) -> str:
    return f"node_{_safe_id(name)}"


def _output_node_id(name: str) -> str:
    return f"out_{_safe_id(name)}"


def _safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value)


def _escape_dot(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


_MISSING = object()
