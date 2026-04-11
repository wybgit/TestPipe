"""Case-level validation against compiled pipeline contracts."""

from __future__ import annotations

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

        for missing_name in sorted(required_input_names - set(case_spec.inputs.keys())):
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

        if not case_spec.expected:
            issues.append(
                IssueSpec(
                    level="warn",
                    field="expected",
                    message="expected is empty; execution can run, but there is no business assertion",
                )
            )
            fix_suggestions.append("补充至少一个业务断言到 expected")

        has_error = any(item.level == "error" for item in issues)
        has_warn = any(item.level == "warn" for item in issues)
        status = "fail" if has_error else "warn" if has_warn else "pass"
        return CaseCheckReport(
            status=status,
            issues=issues,
            fix_suggestions=fix_suggestions,
            normalized_case=case_spec.to_dict(),
        )
