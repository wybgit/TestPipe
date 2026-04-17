"""Runtime and CLI tests for the supported TestPipe workflow."""

from __future__ import annotations

import io
import json
import subprocess
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


class RuntimeCliTest(unittest.TestCase):
    def _run(self, cmd: list[str], cwd: str | None = None) -> None:
        subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)

    def _create_git_resource_repo(self, root: Path) -> tuple[str, str]:
        repo_dir = root / "onnx-layer"
        repo_dir.mkdir(parents=True, exist_ok=True)
        self._run(["git", "init"], cwd=str(repo_dir))
        self._run(["git", "config", "user.email", "test@example.com"], cwd=str(repo_dir))
        self._run(["git", "config", "user.name", "TestPipe"], cwd=str(repo_dir))
        resource_dir = repo_dir / "Abs_testcase_5a6b43" / "resources"
        resource_dir.mkdir(parents=True, exist_ok=True)
        (resource_dir / "Abs_testcase_5a6b43.onnx").write_text("fake onnx payload\n", encoding="utf-8")
        self._run(["git", "add", "."], cwd=str(repo_dir))
        self._run(["git", "commit", "-m", "init resource"], cwd=str(repo_dir))
        self._run(["git", "checkout", "-b", "Abs"], cwd=str(repo_dir))
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo_dir), check=True, capture_output=True, text=True).stdout.strip()
        return str(repo_dir), commit

    def _create_fake_atc_env(self, root: Path) -> str:
        bin_dir = root / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        atc_script = bin_dir / "atc"
        atc_script.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env bash",
                    "set -euo pipefail",
                    "output=\"\"",
                    "model=\"\"",
                    "for arg in \"$@\"; do",
                    "  case \"$arg\" in",
                    "    --output=*) output=\"${arg#*=}\" ;;",
                    "    --model=*) model=\"${arg#*=}\" ;;",
                    "  esac",
                    "done",
                    "cp \"$model\" \"${output}.om\"",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        atc_script.chmod(0o755)
        env_script = root / "set_env.sh"
        env_script.write_text(f"#!/usr/bin/env bash\nexport PATH={bin_dir}:$PATH\n", encoding="utf-8")
        env_script.chmod(0o755)
        return str(env_script)

    def _onnx_case_document(self, *, repo: str, env_script: str, case_ids: list[str]) -> dict[str, object]:
        return {
            "pipeline": {
                "name": "OnnxGitAtcPipeline",
                "nodes": {
                    "fetchModelNode": {
                        "repo": repo,
                        "branch": "Abs",
                        "path": "Abs_testcase_5a6b43",
                        "model_pattern": "*.onnx",
                    },
                    "compileModelNode": {
                        "env_script": env_script,
                        "soc_version": "Ascend310P3",
                    },
                },
            },
            "cases": [
                {
                    "case_id": case_id,
                    "expected": {
                        "om_path": {
                            "exists": True,
                        }
                    },
                }
                for case_id in case_ids
            ],
        }

    def _write_case_file(self, root: Path, name: str, payload: dict[object, object]) -> Path:
        path = root / name
        path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return path

    def test_case_checker_reports_missing_required_input(self) -> None:
        bootstrap()
        case = TestCaseLoader().load_data(
            {
                "pipeline": {"name": "OnnxGitAtcPipeline"},
                "cases": [
                    {
                        "case_id": "onnx_case",
                        "fetchModelNode": {"repo": "repo", "path": "model"},
                        "compileModelNode": {"soc_version": "Ascend310P3"},
                    }
                ],
            }
        )
        pipeline_spec = PipelineCompiler().compile(create_pipeline(case.pipeline))

        report = CaseChecker().check(case, pipeline_spec)
        self.assertEqual(report.status, "fail")
        self.assertEqual(report.issues[0].field, "inputs_by_node.fetchModelNode.branch")

    def test_check_case_cli_returns_structured_failure(self) -> None:
        bootstrap()
        invalid_case = {
            "test_case": {
                "case_id": "bad_case",
                "name": "BadCase",
                "pipeline": "OnnxGitAtcPipeline",
                "inputs": {},
                "inputs_by_node": {
                    "fetchModelNode": {"repo": "repo", "branch": "main", "path": "model"},
                    "compileModelNode": {"soc_version": "Ascend310P3"},
                },
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
        self.assertIn('"field": "expected.unknown_output"', stdout.getvalue())

    def test_run_cli_accepts_env_profile_file(self) -> None:
        bootstrap()
        framework_config = {
            "testpipe": {
                "default_env": "local",
                "envs": {
                    "local": {"enabled": True, "host": {"mode": "local"}},
                    "custom_local": {
                        "enabled": True,
                        "host": {
                            "mode": "local",
                        },
                        "transport": {
                            "mode": "local",
                            "size_threshold_mb": 64,
                        },
                        "metadata": {
                            "profile_name": "custom_local",
                        },
                    },
                },
            }
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_file = Path(tmp_dir) / "testpipe.config.yaml"
            config_file.write_text(yaml.safe_dump(framework_config, allow_unicode=True, sort_keys=False), encoding="utf-8")
            repo_dir, _ = self._create_git_resource_repo(Path(tmp_dir))
            env_script = self._create_fake_atc_env(Path(tmp_dir))
            case_file = self._write_case_file(Path(tmp_dir), "onnx.yaml", self._onnx_case_document(repo=repo_dir, env_script=env_script, case_ids=["onnx_case"]))
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(
                    [
                        "run",
                        str(case_file),
                        "--output-root",
                        tmp_dir,
                        "--config",
                        str(config_file),
                        "--env-profile",
                        "custom_local",
                        "--debug",
                    ]
                )
            self.assertEqual(exit_code, 0)
            run_dirs = [path for path in Path(tmp_dir).iterdir() if path.is_dir() and (path / "summary.json").exists()]
            self.assertEqual(len(run_dirs), 1)
            env_snapshot = json.loads((run_dirs[0] / "env_profile.json").read_text(encoding="utf-8"))
            self.assertEqual(env_snapshot["host"]["mode"], "local")
            self.assertEqual(env_snapshot["metadata"]["profile_name"], "custom_local")

    def test_export_pipeline_graph_cli_writes_dot_and_pdf(self) -> None:
        bootstrap()
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_dir, _ = self._create_git_resource_repo(Path(tmp_dir))
            env_script = self._create_fake_atc_env(Path(tmp_dir))
            case_file = self._write_case_file(
                Path(tmp_dir),
                "onnx.yaml",
                self._onnx_case_document(repo=repo_dir, env_script=env_script, case_ids=["onnx_case"]),
            )
            export_dir = Path(tmp_dir) / "exports"
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(
                    [
                        "export-pipeline-graph",
                        str(case_file),
                        "--output-dir",
                        str(export_dir),
                        "--json",
                    ]
                )
            self.assertEqual(exit_code, 0)
            payload = json.loads(buffer.getvalue())
            dot_path = Path(payload["dot_path"])
            pdf_path = Path(payload["pdf_path"])
            self.assertTrue(dot_path.exists())
            self.assertTrue(pdf_path.exists())
            dot_text = dot_path.read_text(encoding="utf-8")
            self.assertIn("OnnxGitAtcPipeline", dot_text)
            self.assertIn("rankdir=TB", dot_text)
            self.assertIn("Ascend310P3", dot_text)
            self.assertIn("INPUT", dot_text)
            self.assertIn("PARAMS", dot_text)
            self.assertIn("compileModelNode", dot_text)
            self.assertNotIn("resource_ref", dot_text)
            self.assertNotIn("atc_options", dot_text)
            self.assertNotIn("<pipeline:atc_options>", dot_text)
            self.assertIn("output_name: model.om", dot_text)
            self.assertNotIn("COMMANDS", dot_text)


if __name__ == "__main__":
    unittest.main()
