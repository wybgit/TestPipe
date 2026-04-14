"""Tests for built-in LLM-native templates and skills."""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import yaml

from testpipe import bootstrap
from testpipe.cli.main import main
from testpipe.core import PipelineCompiler, create_pipeline
from testpipe.loaders import TestCaseLoader
from testpipe.skills import get_skill, list_skills
from testpipe.templates import get_template, list_templates
from testpipe.validation import CaseChecker


class LLMAssetRegistryTest(unittest.TestCase):
    def test_builtin_templates_are_registered(self) -> None:
        bootstrap()
        self.assertEqual(
            list_templates(),
            [
                "case-check-template",
                "case-template",
                "pipeline-template",
                "result-analysis-template",
                "run-template",
                "test-op-template",
            ],
        )
        template = get_template("case-template")
        self.assertEqual(template.task_type, "generate_case")
        self.assertEqual(template.body["pipeline"]["name"], "PipelineName")

    def test_builtin_skills_are_registered(self) -> None:
        bootstrap()
        self.assertEqual(
            list_skills(),
            [
                "case-checker",
                "case-generator",
                "case-runner",
                "pipeline-generator",
                "result-analyzer",
                "test-op-generator",
            ],
        )
        skill = get_skill("pipeline-generator")
        self.assertEqual(skill.template_name, "pipeline-template")
        self.assertIn("PipelineSpec", skill.contract["outputs"])

    def test_cli_can_show_template_and_skill(self) -> None:
        bootstrap()
        template_stdout = io.StringIO()
        with redirect_stdout(template_stdout):
            exit_code = main(["show-template", "case-template"])
        self.assertEqual(exit_code, 0)
        self.assertIn("task_type: generate_case", template_stdout.getvalue())

        skill_stdout = io.StringIO()
        with redirect_stdout(skill_stdout):
            exit_code = main(["show-skill", "case-runner", "--json"])
        self.assertEqual(exit_code, 0)
        self.assertIn('"template_name": "run-template"', skill_stdout.getvalue())

    def test_case_checker_reports_missing_required_input(self) -> None:
        bootstrap()
        case = TestCaseLoader().load_data(
            {
                "pipeline": {"name": "SmokePipeline"},
                "cases": [{"case_id": "smoke_case", "echo": {"message": "hello"}}],
            }
        )
        case.inputs.pop("message")
        case.inputs_by_node["echo"].pop("message")
        pipeline_spec = PipelineCompiler().compile(create_pipeline(case.pipeline))

        report = CaseChecker().check(case, pipeline_spec)
        self.assertEqual(report.status, "fail")
        self.assertEqual(report.issues[0].field, "inputs.message")

    def test_check_case_cli_returns_structured_failure(self) -> None:
        bootstrap()
        invalid_case = {
            "test_case": {
                "case_id": "bad_case",
                "name": "BadCase",
                "pipeline": "SmokePipeline",
                "inputs": {},
                "expected": {"unknown_output": True},
            }
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_file = Path(tmp_dir) / "bad_case.yaml"
            case_file.write_text(yaml.safe_dump(invalid_case, allow_unicode=True, sort_keys=False), encoding="utf-8")

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["check-case", str(case_file), "--json"])

        self.assertEqual(exit_code, 2)
        self.assertIn('"status": "fail"', stdout.getvalue())
        self.assertIn('"field": "inputs.message"', stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
