"""Tests for suite-style testcase loading and validation."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import yaml

from testpipe import bootstrap
from testpipe.cli.main import main
from testpipe.core import PipelineCompiler, create_pipeline
from testpipe.loaders import TestCaseLoader
from testpipe.validation import CaseChecker


class TestCaseSuiteTest(unittest.TestCase):
    def _write_case_file(self, root: Path, name: str, payload: dict[object, object]) -> Path:
        path = root / name
        path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return path

    def test_single_case_supports_vars_and_inputs_by_node(self) -> None:
        bootstrap()
        payload = {
            "pipeline": {
                "name": "SmokePipeline",
            },
            "cases": [
                {
                    "case_id": "single_case",
                    "echo": {
                        "message": "hello single",
                    },
                }
            ],
        }

        case = TestCaseLoader().load_data(payload)
        self.assertEqual(case.name, "")
        self.assertEqual(case.variables, {})
        self.assertEqual(case.inputs["message"], "hello single")
        self.assertEqual(case.inputs_by_node["echo"]["message"], "hello single")
        self.assertEqual(case.expected, {})

    def test_suite_loads_globals_and_case_overrides(self) -> None:
        bootstrap()
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_file = self._write_case_file(
                Path(tmp_dir),
                "suite.yaml",
                {
                    "pipeline": {
                        "name": "SmokePipeline",
                        "echo": {"message": "hello suite"},
                    },
                    "cases": [
                        {"case_id": "smoke_suite_default"},
                        {"case_id": "smoke_suite_override", "echo": {"message": "hello suite override"}},
                    ],
                },
            )
            cases = TestCaseLoader().load_many(case_file)
        self.assertEqual([case.case_id for case in cases], ["smoke_suite_default", "smoke_suite_override"])
        self.assertEqual(cases[0].inputs["message"], "hello suite")
        self.assertEqual(cases[1].inputs["message"], "hello suite override")
        self.assertEqual(cases[0].expected, {})
        self.assertEqual(cases[1].expected, {})

    def test_checker_rejects_invalid_or_overwritten_node_inputs(self) -> None:
        bootstrap()
        pipeline_spec = PipelineCompiler().compile(create_pipeline("SmokePipeline"))
        payload = {
            "pipeline": {
                "name": "SmokePipeline",
            },
            "cases": [
                {
                    "case_id": "bad_node_mapping",
                    "echo": {"env_ready": False},
                    "missing_node": {"message": "hello"},
                }
            ],
        }

        case = TestCaseLoader().load_data(payload)
        report = CaseChecker().check(case, pipeline_spec)
        self.assertEqual(report.status, "fail")
        issue_fields = {issue.field for issue in report.issues}
        self.assertIn("inputs_by_node.echo.env_ready", issue_fields)
        self.assertIn("inputs_by_node.missing_node", issue_fields)

    def test_loader_rejects_duplicate_case_ids(self) -> None:
        bootstrap()
        payload = {
            "pipeline": {"name": "SmokePipeline"},
            "cases": [
                {"case_id": "dup_case", "echo": {"message": "hello"}},
                {"case_id": "dup_case", "echo": {"message": "world"}},
            ],
        }
        with self.assertRaisesRegex(ValueError, "duplicate case_id"):
            TestCaseLoader().load_many_data(payload)

    def test_check_case_cli_supports_multi_case_aggregation_and_selection(self) -> None:
        bootstrap()
        suite = {
            "pipeline": {
                "name": "SmokePipeline",
            },
            "cases": [
                {"case_id": "case_a", "echo": {"message": "hello"}},
                {"case_id": "case_b", "echo": {"message": "world"}},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_file = Path(tmp_dir) / "suite.yaml"
            case_file.write_text(yaml.safe_dump(suite, allow_unicode=True, sort_keys=False), encoding="utf-8")

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["check-case", str(case_file), "--json"])
            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["case_count"], 2)
            self.assertEqual(payload["status"], "pass")

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["check-case", str(case_file), "--case-id", "case_b", "--json"])
            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["normalized_case"]["case_id"], "case_b")

    def test_run_cli_executes_all_cases_in_suite(self) -> None:
        bootstrap()
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_file = self._write_case_file(
                Path(tmp_dir),
                "suite.yaml",
                {
                    "pipeline": {"name": "SmokePipeline"},
                    "cases": [
                        {
                            "case_id": "smoke_suite_default",
                            "description": "default suite case",
                            "level": "P1",
                            "echo": {"message": "hello suite"},
                        },
                        {
                            "case_id": "smoke_suite_override",
                            "description": "override suite case",
                            "level": "P0",
                            "echo": {"message": "hello suite override"},
                        },
                    ],
                },
            )
            exit_code = main(["run", str(case_file), "--output-root", tmp_dir])
            self.assertEqual(exit_code, 0)
            run_dirs = sorted(path for path in Path(tmp_dir).iterdir() if path.is_dir())
            self.assertEqual(len([path for path in run_dirs if (path / "summary.json").exists()]), 2)
            summary_files = [path / "summary.json" for path in run_dirs if (path / "summary.json").exists()]
            self.assertTrue(all(path.exists() for path in summary_files))
            summary_payloads = [json.loads(path.read_text(encoding="utf-8")) for path in summary_files]
            self.assertTrue(all("description" in item for item in summary_payloads))
            self.assertTrue(all("level" in item for item in summary_payloads))
            self.assertTrue(all("case_name" not in item for item in summary_payloads))


if __name__ == "__main__":
    unittest.main()
