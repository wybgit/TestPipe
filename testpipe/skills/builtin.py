"""Built-in LLM-native skill contracts."""

from __future__ import annotations

from testpipe.skills.registry import register_skill
from testpipe.spec import SkillSpec


register_skill(
    SkillSpec(
        name="test-op-generator",
        category="generator",
        template_name="test-op-template",
        description="Generate TestOp draft artifacts from the test-op template",
        contract={
            "input": "test-op-template",
            "outputs": ["OpSpec", "python_op_draft", "unit_test_draft", "doc_draft"],
        },
    )
)

register_skill(
    SkillSpec(
        name="pipeline-generator",
        category="generator",
        template_name="pipeline-template",
        description="Generate PipelineSpec, DSL draft, and graph draft from the pipeline template",
        contract={
            "input": "pipeline-template",
            "outputs": ["PipelineSpec", "python_pipeline_draft", "mermaid_graph"],
        },
    )
)

register_skill(
    SkillSpec(
        name="case-generator",
        category="generator",
        template_name="case-template",
        description="Generate CaseSpec and YAML testcase draft from the case template",
        contract={
            "input": "case-template",
            "outputs": ["CaseSpec", "yaml_case_draft"],
        },
    )
)

register_skill(
    SkillSpec(
        name="case-checker",
        category="checker",
        template_name="case-check-template",
        description="Check testcase completeness, compatibility, and fix hints",
        contract={
            "input": "case-check-template",
            "outputs": ["check_report", "normalized_case"],
        },
    )
)

register_skill(
    SkillSpec(
        name="case-runner",
        category="runner",
        template_name="run-template",
        description="Translate run-template input into executable run plan and command",
        contract={
            "input": "run-template",
            "outputs": ["run_command", "run_plan_summary", "result_location"],
        },
    )
)

register_skill(
    SkillSpec(
        name="result-analyzer",
        category="analyzer",
        template_name="result-analysis-template",
        description="Analyze summary, trace, and step logs into structured conclusions",
        contract={
            "input": "result-analysis-template",
            "outputs": ["analysis_report", "root_cause", "fix_suggestions"],
        },
    )
)
