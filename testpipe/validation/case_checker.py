"""Case-level validation against compiled pipeline contracts."""

from __future__ import annotations

from testpipe.core import get_op_class
from testpipe.spec import CaseCheckReport, IssueSpec


class CaseChecker:
    """Validate a CaseSpec against the compiled PipelineSpec contract."""

    def check(self, case_spec, pipeline_spec) -> CaseCheckReport:
        issues: list[IssueSpec] = []
        fix_suggestions: list[str] = []

        if case_spec.pipeline != pipeline_spec.name:
            issues.append(
                IssueSpec(
                    level="error",
                    field="pipeline",
                    message=f"case pipeline '{case_spec.pipeline}' does not match compiled pipeline '{pipeline_spec.name}'",
                )
            )
            fix_suggestions.append(f"将 case.pipeline 修正为 {pipeline_spec.name}")

        input_names = {item.name for item in pipeline_spec.inputs}
        required_input_names = {item.name for item in pipeline_spec.inputs if item.required}
        node_specs = pipeline_spec.node_map()
        edge_targets: dict[str, set[str]] = {}
        node_bindings: dict[str, dict[str, object]] = {}
        for node in pipeline_spec.nodes:
            for binding in node.input_bindings:
                edge_targets.setdefault(node.name, set()).add(binding.target_port)
                node_bindings.setdefault(node.name, {})[binding.target_port] = binding

        satisfied_pipeline_inputs = set(case_spec.inputs.keys())
        for node_name, node_inputs in case_spec.inputs_by_node.items():
            connected_ports = edge_targets.get(node_name, set())
            for port_name in node_inputs:
                if port_name in connected_ports:
                    continue
                if port_name in input_names:
                    satisfied_pipeline_inputs.add(port_name)

        for missing_name in sorted(required_input_names - satisfied_pipeline_inputs):
            issues.append(
                IssueSpec(
                    level="error",
                    field=f"inputs.{missing_name}",
                    message="missing required pipeline input",
                )
            )
            fix_suggestions.append(f"补充 inputs.{missing_name}")

        for extra_name in sorted(set(case_spec.inputs.keys()) - input_names):
            issues.append(
                IssueSpec(
                    level="warn",
                    field=f"inputs.{extra_name}",
                    message="input is not declared in pipeline inputs",
                )
            )
            fix_suggestions.append(f"确认是否需要删除 inputs.{extra_name} 或更新 Pipeline 输入定义")

        for node_name, node_inputs in sorted(case_spec.inputs_by_node.items()):
            if node_name not in node_specs:
                issues.append(
                    IssueSpec(
                        level="error",
                        field=f"inputs_by_node.{node_name}",
                        message="node is not declared in pipeline graph",
                    )
                )
                fix_suggestions.append(f"将 inputs_by_node.{node_name} 修正为 Pipeline 中真实存在的节点名")
                continue

            node_spec = node_specs[node_name]
            op_class = get_op_class(node_spec.op_name)
            op_input_names = {item.name for item in op_class.spec.inputs}
            connected_ports = edge_targets.get(node_name, set())
            for port_name in sorted(node_inputs):
                if port_name not in op_input_names:
                    issues.append(
                        IssueSpec(
                            level="error",
                            field=f"inputs_by_node.{node_name}.{port_name}",
                            message=f"port is not declared by op '{node_spec.op_name}'",
                        )
                    )
                    fix_suggestions.append(f"检查节点 {node_name} 的输入端口名，删除或修正 {port_name}")
                    continue
                if port_name in connected_ports:
                    binding = node_bindings.get(node_name, {}).get(port_name)
                    if binding is not None and getattr(binding, "source_type", "") == "pipeline_input":
                        continue
                    issues.append(
                        IssueSpec(
                            level="error",
                            field=f"inputs_by_node.{node_name}.{port_name}",
                            message="port is driven by an upstream edge; testcase assignment would be overwritten",
                        )
                    )
                    fix_suggestions.append(f"不要在用例里为 {node_name}.{port_name} 赋值，改为修改其上游节点或 Pipeline 设计")

        output_names = {item.name for item in pipeline_spec.outputs}
        for expected_name in sorted(case_spec.expected.keys()):
            if expected_name in output_names:
                continue
            issues.append(
                IssueSpec(
                    level="error",
                    field=f"expected.{expected_name}",
                    message="expected field is not declared in pipeline outputs",
                )
            )
            fix_suggestions.append(f"删除 expected.{expected_name} 或把该输出加入 Pipeline outputs")

        has_error = any(item.level == "error" for item in issues)
        has_warn = any(item.level == "warn" for item in issues)
        status = "fail" if has_error else "warn" if has_warn else "pass"
        return CaseCheckReport(
            status=status,
            issues=issues,
            fix_suggestions=fix_suggestions,
            normalized_case=case_spec.to_dict(),
        )
