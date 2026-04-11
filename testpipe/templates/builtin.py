"""Built-in LLM-native templates."""

from __future__ import annotations

from testpipe.spec import TemplateSpec
from testpipe.templates.registry import register_template


register_template(
    TemplateSpec(
        name="test-op-template",
        task_type="generate_test_op",
        description="Generate a new TestOp definition, code draft, and test draft",
        body={
            "task_type": "generate_test_op",
            "op_name": "",
            "op_category": "",
            "business_goal": "",
            "inputs": [{"name": "", "type": "", "description": ""}],
            "outputs": [{"name": "", "type": "", "description": ""}],
            "attributes": [{"name": "", "type": "", "default": None, "description": ""}],
            "dependencies": {"host_tools": [], "device_tools": []},
            "side_effects": [],
            "validation_rules": [],
            "examples": [],
        },
    )
)

register_template(
    TemplateSpec(
        name="pipeline-template",
        task_type="generate_pipeline",
        description="Generate a pipeline graph and Pipeline DSL draft",
        body={
            "task_type": "generate_pipeline",
            "pipeline_name": "",
            "business_goal": "",
            "pipeline_inputs": [],
            "pipeline_outputs": [],
            "stages": [{"name": "", "goal": ""}],
            "required_ops": [],
            "optional_ops": [],
            "data_flow_notes": [],
            "constraints": {"allow_parallel": False, "requires_device": False},
            "expected_artifacts": [],
        },
    )
)

register_template(
    TemplateSpec(
        name="case-template",
        task_type="generate_case",
        description="Generate a structured CaseSpec and YAML testcase draft",
        body={
            "task_type": "generate_case",
            "case_name": "",
            "target_pipeline": "",
            "test_goal": "",
            "inputs": {},
            "expected": {},
            "dataset_mode": "single",
            "tags": [],
            "priority": "P2",
            "environment_hint": "",
        },
    )
)

register_template(
    TemplateSpec(
        name="case-check-template",
        task_type="check_case",
        description="Check a generated testcase against pipeline contract and execution assumptions",
        body={
            "task_type": "check_case",
            "pipeline_spec_ref": "",
            "case_spec": {},
            "check_items": ["schema", "required_inputs", "expected_rules", "environment_match"],
            "strict_mode": True,
        },
    )
)

register_template(
    TemplateSpec(
        name="run-template",
        task_type="run_case",
        description="Generate an execution request and run plan summary",
        body={
            "task_type": "run_case",
            "case_ref": "",
            "pipeline_ref": "",
            "env_profile": "",
            "output_dir": "",
            "log_level": "INFO",
            "rerun_failed_only": False,
            "artifacts_policy": "keep_all",
        },
    )
)

register_template(
    TemplateSpec(
        name="result-analysis-template",
        task_type="analyze_result",
        description="Generate a structured failure analysis or execution summary",
        body={
            "task_type": "analyze_result",
            "case_ref": "",
            "summary_ref": "",
            "trace_ref": "",
            "focus": ["failed_step", "root_cause", "retryability", "fix_suggestion"],
            "comparison_baseline": "",
        },
    )
)
