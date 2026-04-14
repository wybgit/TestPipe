from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from testpipe import bootstrap
from testpipe.core import PipelineCompiler, create_pipeline
from testpipe.engine import TestEngine
from testpipe.engine.context import MappingView, StepContext
from testpipe.infra import ActionRunner, ArtifactStore, HostExecutor, TraceRecorder
from testpipe.ops.builtin import ATCCompileOp, ResourceFetchOp
from testpipe.spec import CaseSpec, EnvProfile


def _run(cmd: list[str], cwd: str | None = None) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


class AtcMainlineFlowTest(unittest.TestCase):
    def _create_git_resource_repo(self, root: Path) -> tuple[str, str]:
        repo_dir = root / "onnx-layer"
        repo_dir.mkdir(parents=True, exist_ok=True)
        _run(["git", "init"], cwd=str(repo_dir))
        _run(["git", "config", "user.email", "test@example.com"], cwd=str(repo_dir))
        _run(["git", "config", "user.name", "TestPipe"], cwd=str(repo_dir))
        resource_dir = repo_dir / "Abs_testcase_5a6b43" / "resources"
        resource_dir.mkdir(parents=True, exist_ok=True)
        (resource_dir / "Abs_testcase_5a6b43.onnx").write_text("fake onnx payload\n", encoding="utf-8")
        (resource_dir / "Abs_testcase_5a6b43.json").write_text('{"name": "abs"}\n', encoding="utf-8")
        _run(["git", "add", "."], cwd=str(repo_dir))
        _run(["git", "commit", "-m", "init resource"], cwd=str(repo_dir))
        _run(["git", "checkout", "-b", "Abs"], cwd=str(repo_dir))
        commit = (
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(repo_dir),
                check=True,
                capture_output=True,
                text=True,
            )
            .stdout.strip()
        )
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
                    "args_file=\"\"",
                    "for arg in \"$@\"; do",
                    "  case \"$arg\" in",
                    "    --output=*) output=\"${arg#*=}\" ;;",
                    "    --model=*) model=\"${arg#*=}\" ;;",
                    "    --args_file=*) args_file=\"${arg#*=}\" ;;",
                    "  esac",
                    "done",
                    "if [ -n \"$args_file\" ]; then",
                    "  printf '%s\\n' \"$@\" > \"$args_file\"",
                    "fi",
                    "cp \"$model\" \"${output}.om\"",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        atc_script.chmod(0o755)

        env_script = root / "set_env.sh"
        env_script.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env bash",
                    f"export PATH={bin_dir}:$PATH",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        env_script.chmod(0o755)
        return str(env_script)

    def _build_step_context(self, root: Path, *, node_name: str, inputs: dict[str, object], attrs: dict[str, object]) -> StepContext:
        run_dir = root / "run"
        step_dir = run_dir / "steps" / node_name
        step_dir.mkdir(parents=True, exist_ok=True)
        trace = TraceRecorder(run_dir / "trace.json")
        action_runner = ActionRunner(trace)
        placeholder = SimpleNamespace(
            node_name=node_name,
            stdout_log_path=str(step_dir / "stdout.log"),
            stderr_log_path=str(step_dir / "stderr.log"),
        )
        host = HostExecutor(action_runner, placeholder)
        context = StepContext(
            node_name=node_name,
            step_dir=str(step_dir),
            stdout_log_path=str(step_dir / "stdout.log"),
            stderr_log_path=str(step_dir / "stderr.log"),
            inputs=MappingView(inputs),
            attrs=MappingView(attrs),
            host=host,
            device=None,
            transfer=None,
            artifacts=ArtifactStore(run_dir / "artifacts"),
            logger_name=f"test.{node_name}",
            debug=True,
        )
        host.step_context = context
        return context

    def test_resource_fetch_op_can_materialize_git_directory(self) -> None:
        bootstrap()
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_dir, commit = self._create_git_resource_repo(Path(tmp_dir))
            context = self._build_step_context(
                Path(tmp_dir),
                node_name="fetchModelNode",
                inputs={
                    "repo": repo_dir,
                    "ref": "Abs",
                    "path": "Abs_testcase_5a6b43",
                    "model_pattern": "*.onnx",
                },
                attrs={},
            )
            outputs = ResourceFetchOp().execute(context)
            self.assertEqual(outputs["resolved_commit"], commit)
            self.assertTrue(Path(outputs["resource_root"]).exists())
            self.assertTrue(Path(outputs["model_path"]).exists())
            self.assertEqual(Path(outputs["resource_root"]).name, "Abs_testcase_5a6b43")
            self.assertEqual(Path(outputs["model_path"]).name, "Abs_testcase_5a6b43.onnx")
            self.assertFalse((Path(tmp_dir) / "run" / "steps" / "fetchModelNode" / "git_materialized").exists())

    def test_resource_fetch_op_can_fallback_to_github_archive(self) -> None:
        bootstrap()
        with tempfile.TemporaryDirectory() as tmp_dir:
            archive_root = Path(tmp_dir) / "archive" / "onnx-layer-commit"
            resource_dir = archive_root / "Abs_testcase_5a6b43" / "resources"
            resource_dir.mkdir(parents=True, exist_ok=True)
            (resource_dir / "Abs_testcase_5a6b43.onnx").write_text("fake onnx payload\n", encoding="utf-8")
            context = self._build_step_context(
                Path(tmp_dir),
                node_name="fetchModelNode",
                inputs={
                    "repo": "https://github.com/wybgit/onnx-layer.git",
                    "ref": "Abs",
                    "path": "Abs_testcase_5a6b43",
                    "model_pattern": "*.onnx",
                },
                attrs={},
            )

            def fake_git_fetch(*args, **kwargs):
                raise RuntimeError("simulated git transport failure")

            def fake_archive_fetch(step_context, *, repo, subpath, git_ref, target_root, cause):
                self.assertEqual(repo, "https://github.com/wybgit/onnx-layer.git")
                self.assertEqual(git_ref, "Abs")
                self.assertEqual(subpath, "Abs_testcase_5a6b43")
                materialized_path = ResourceFetchOp()._materialize_local_resource(archive_root / subpath, target_root)  # noqa: SLF001
                return materialized_path, "archive_commit"

            with (
                patch.object(ResourceFetchOp, "_fetch_git_dir_via_git", side_effect=fake_git_fetch),
                patch.object(ResourceFetchOp, "_fetch_git_dir_via_github_archive", side_effect=fake_archive_fetch),
            ):
                outputs = ResourceFetchOp().execute(context)

            self.assertEqual(outputs["resolved_commit"], "archive_commit")
            self.assertTrue(Path(outputs["resource_root"]).exists())
            self.assertEqual(Path(outputs["resource_root"]).name, "Abs_testcase_5a6b43")
            self.assertEqual(Path(outputs["model_path"]).name, "Abs_testcase_5a6b43.onnx")

    def test_atc_compile_op_supports_extra_args(self) -> None:
        bootstrap()
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_script = self._create_fake_atc_env(Path(tmp_dir))
            args_log = Path(tmp_dir) / "atc_args.log"
            model_path = Path(tmp_dir) / "model.onnx"
            model_path.write_text("fake model\n", encoding="utf-8")
            context = self._build_step_context(
                Path(tmp_dir),
                node_name="compileModelNode",
                inputs={
                    "model_path": str(model_path),
                    "soc_version": "Ascend310P3",
                    "env_script": env_script,
                    "output_name": "custom_model.om",
                    "atc_options": {
                        "precision_mode": "allow_fp32_to_fp16",
                        "input_format": "NCHW",
                        "args_file": str(args_log),
                    },
                },
                attrs={"output_name": "model.om", "timeout": 30, "framework": 5, "env_script": env_script},
            )
            outputs = ATCCompileOp(output_name="model.om", timeout=30, framework=5, env_script=env_script).execute(context)
            self.assertTrue(Path(outputs["om_path"]).exists())
            logged_args = args_log.read_text(encoding="utf-8")
            self.assertIn("--precision_mode=allow_fp32_to_fp16", logged_args)
            self.assertIn("--input_format=NCHW", logged_args)
            self.assertIn("--soc_version=Ascend310P3", logged_args)
            logged_args_lines = [line.strip() for line in logged_args.splitlines() if line.strip()]
            self.assertEqual(
                logged_args_lines[:4],
                [
                    f"--model={model_path}",
                    "--framework=5",
                    f"--output={Path(tmp_dir) / 'run' / 'steps' / 'compileModelNode' / 'custom_model'}",
                    "--soc_version=Ascend310P3",
                ],
            )

    def test_build_atc_command_matches_reference_order(self) -> None:
        bootstrap()
        op = ATCCompileOp()
        command = op._build_atc_command(  # noqa: SLF001
            model_path=Path("/tmp/Abs_testcase_5a6b43.onnx"),
            output_prefix=Path("/tmp/Abs_testcase_5a6b43"),
            framework=5,
            soc_version="Ascend310P3",
            atc_options=None,
        )
        self.assertEqual(
            command,
            [
                "atc",
                "--model=/tmp/Abs_testcase_5a6b43.onnx",
                "--framework=5",
                "--output=/tmp/Abs_testcase_5a6b43",
                "--soc_version=Ascend310P3",
            ],
        )

    def test_atc_compile_op_rejects_reserved_extra_args(self) -> None:
        bootstrap()
        op = ATCCompileOp()
        with self.assertRaisesRegex(RuntimeError, "reserved argument: model"):
            op._render_extra_atc_args({"model": "override.onnx"})  # noqa: SLF001

    def test_onnx_git_atc_pipeline_executes_with_fake_atc(self) -> None:
        bootstrap()
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_dir, commit = self._create_git_resource_repo(Path(tmp_dir))
            env_script = self._create_fake_atc_env(Path(tmp_dir))
            case = CaseSpec(
                case_id="onnx_git_atc_case",
                name="OnnxGitAtcPipeline_Basic",
                pipeline="OnnxGitAtcPipeline",
                inputs={},
                inputs_by_node={
                    "fetchModelNode": {
                        "repo": repo_dir,
                        "ref": "Abs",
                        "path": "Abs_testcase_5a6b43",
                        "model_pattern": "*.onnx",
                    },
                    "compileModelNode": {
                        "soc_version": "Ascend310P3",
                        "env_script": env_script,
                        "output_name": "abs_model.om",
                        "atc_options": {"precision_mode": "allow_fp32_to_fp16"},
                    },
                    "assertOmExistsNode": {
                        "expected_value": True,
                    },
                },
            )
            pipeline = create_pipeline(case.pipeline)
            pipeline_spec = PipelineCompiler().compile(pipeline)
            summary = TestEngine(output_root=Path(tmp_dir) / "runs", debug=False).execute(
                case_spec=case,
                pipeline_spec=pipeline_spec,
                env_profile=EnvProfile.local_default(),
            )
            self.assertEqual(summary.status, "passed")
            self.assertEqual(summary.outputs["resolved_commit"], commit)
            self.assertTrue(Path(str(summary.outputs["model_path"])).exists())
            self.assertTrue(Path(str(summary.outputs["om_path"])).exists())
            self.assertTrue(summary.outputs["path_exists"])
            self.assertTrue(summary.outputs["test_passed"])


if __name__ == "__main__":
    unittest.main()
