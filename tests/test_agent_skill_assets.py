"""Tests for external agent skill assets and helper scripts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


class AgentSkillAssetsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.skills_root = self.repo_root / "skills"

    def test_catalog_contains_four_agent_skills(self) -> None:
        catalog_file = self.skills_root / "catalog.yaml"
        payload = yaml.safe_load(catalog_file.read_text(encoding="utf-8"))
        self.assertEqual(
            [item["name"] for item in payload["skills"]],
            [
                "test-node",
                "test-pipeline",
                "test-case-generation",
                "test-result-analysis",
            ],
        )

    def test_each_skill_has_skill_markdown_and_template(self) -> None:
        for skill_dir in [
            "test_node",
            "test_pipeline",
            "test_case_generation",
            "test_result_analysis",
        ]:
            self.assertTrue((self.skills_root / skill_dir / "SKILL.md").exists())
            self.assertTrue((self.skills_root / skill_dir / "templates" / "request.template.yaml").exists())
        self.assertTrue((self.skills_root / "test_node" / "scripts" / "generate_scaffold.py").exists())
        self.assertTrue((self.skills_root / "test_pipeline" / "scripts" / "generate_scaffold.py").exists())

    def test_docs_include_agent_skill_guides(self) -> None:
        docs_root = self.repo_root / "docs" / "guides" / "developer"
        self.assertTrue((docs_root / "03_Agent_Skills使用指南.md").exists())
        self.assertFalse((docs_root / "04_Agent_Skills最佳实践.md").exists())

    def test_generate_test_node_scaffold_script(self) -> None:
        script = self.skills_root / "test_node" / "scripts" / "generate_scaffold.py"
        request_file = self.skills_root / "test_node" / "examples" / "request.example.yaml"

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = subprocess.run(
                [sys.executable, str(script), "--request", str(request_file), "--output-root", tmp_dir],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)
            generated = {Path(item).as_posix() for item in payload["written_files"]}
            self.assertIn("testpipe/ops/custom/file_digest.py", generated)
            self.assertIn("tests/test_file_digest_op.py", generated)
            self.assertIn("docs/guides/generated/file_digest_op.md", generated)
            self.assertTrue((Path(tmp_dir) / "testpipe" / "ops" / "custom" / "file_digest.py").exists())

    def test_generate_test_pipeline_scaffold_script(self) -> None:
        script = self.skills_root / "test_pipeline" / "scripts" / "generate_scaffold.py"
        request_file = self.skills_root / "test_pipeline" / "examples" / "request.example.yaml"

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = subprocess.run(
                [sys.executable, str(script), "--request", str(request_file), "--output-root", tmp_dir],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)
            generated = {Path(item).as_posix() for item in payload["written_files"]}
            self.assertIn("testpipe/pipelines/custom/model_fetch_verify.py", generated)
            self.assertIn("examples/testcases/model_fetch_verify.yaml", generated)
            self.assertIn("tests/test_model_fetch_verify_pipeline.py", generated)
            testcase = Path(tmp_dir) / "examples" / "testcases" / "model_fetch_verify.yaml"
            self.assertTrue(testcase.exists())
            testcase_payload = yaml.safe_load(testcase.read_text(encoding="utf-8"))
            self.assertEqual(testcase_payload["pipeline"]["name"], "ModelFetchVerifyPipeline")


if __name__ == "__main__":
    unittest.main()
