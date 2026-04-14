"""Basic framework smoke tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from testpipe import bootstrap
from testpipe.core import PipelineCompiler, create_pipeline
from testpipe.engine import TestEngine
from testpipe.loaders import TestCaseLoader
from testpipe.spec import EnvProfile


class SmokeFrameworkTest(unittest.TestCase):
    def _load_case(self, payload: dict[object, object]) -> object:
        return TestCaseLoader().load_data(payload)

    def test_smoke_pipeline_executes_in_normal_mode(self) -> None:
        bootstrap()
        case = self._load_case(
            {
                "pipeline": {"name": "SmokePipeline"},
                "cases": [{"case_id": "smoke_case", "name": "SmokePipeline_Basic", "echo": {"message": "hello testpipe"}}],
            }
        )
        pipeline = create_pipeline(case.pipeline)
        pipeline_spec = PipelineCompiler().compile(pipeline)

        with tempfile.TemporaryDirectory() as tmp_dir:
            summary = TestEngine(output_root=tmp_dir, debug=False).execute(
                case_spec=case,
                pipeline_spec=pipeline_spec,
                env_profile=EnvProfile.local_default(),
            )
            self.assertEqual(summary.status, "passed")
            self.assertEqual(summary.outputs["echoed_message"], "hello testpipe")

            run_dirs = list(Path(tmp_dir).iterdir())
            self.assertEqual(len(run_dirs), 1)
            run_dir = run_dirs[0]
            summary_path = run_dir / "summary.json"
            self.assertTrue(summary_path.exists())
            summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary_payload["status"], "passed")
            self.assertEqual(summary_payload["case_id"], "smoke_case")
            self.assertIn("run_dir", summary_payload)
            execution_log = run_dir / "execution.log"
            self.assertTrue(execution_log.exists())
            execution_log_text = execution_log.read_text(encoding="utf-8")
            self.assertIn("[PASS][INPUT] 1/3 env_check (EnvCheck)", execution_log_text)
            self.assertIn("[PASS][EXEC] 2/3 host_probe (ShellCommand)", execution_log_text)
            self.assertNotIn("node_type:", execution_log_text)
            self.assertIn("B:", execution_log_text)
            self.assertIn("command: printf smoke-host", execution_log_text)
            self.assertIn("printf smoke-host", execution_log_text)
            self.assertIn("O:", execution_log_text)
            self.assertIn("  - echoed_message: 'hello testpipe'", execution_log_text)
            self.assertNotIn("[CASE ", execution_log_text)
            self.assertFalse((run_dir / "trace.json").exists())
            self.assertFalse((run_dir / "reproduce.sh").exists())
            self.assertFalse((run_dir / "case_spec.yaml").exists())
            self.assertTrue((run_dir / "resources").exists())
            self.assertTrue((run_dir / "steps" / "02_host_probe" / "command.sh").exists())
            self.assertTrue((run_dir / "steps" / "02_host_probe" / "execution.log").exists())
            self.assertTrue((run_dir / "steps" / "02_host_probe" / "result.json").exists())

    def test_smoke_pipeline_executes_in_debug_mode(self) -> None:
        bootstrap()
        case = self._load_case(
            {
                "pipeline": {"name": "SmokePipeline"},
                "cases": [{"case_id": "smoke_case", "name": "SmokePipeline_Basic", "echo": {"message": "hello testpipe"}}],
            }
        )
        pipeline = create_pipeline(case.pipeline)
        pipeline_spec = PipelineCompiler().compile(pipeline)

        with tempfile.TemporaryDirectory() as tmp_dir:
            summary = TestEngine(output_root=tmp_dir, debug=True).execute(
                case_spec=case,
                pipeline_spec=pipeline_spec,
                env_profile=EnvProfile.local_default(),
            )
            self.assertEqual(summary.status, "passed")

            run_dirs = list(Path(tmp_dir).iterdir())
            self.assertEqual(len(run_dirs), 1)
            run_dir = run_dirs[0]
            self.assertTrue((run_dir / "trace.json").exists())
            self.assertTrue((run_dir / "reproduce.sh").exists())
            self.assertTrue((run_dir / "case_spec.yaml").exists())
            self.assertTrue((run_dir / "pipeline_spec.json").exists())
            self.assertTrue((run_dir / "execution.log").exists())
            self.assertTrue((run_dir / "steps" / "02_host_probe" / "command.sh").exists())
            self.assertTrue((run_dir / "steps" / "02_host_probe" / "result.json").exists())

    def test_local_compile_pipeline_materializes_transferred_artifact(self) -> None:
        bootstrap()
        case = self._load_case(
            {
                "pipeline": {"name": "LocalCompilePipeline"},
                "cases": [
                    {
                        "case_id": "local_compile_case",
                        "name": "LocalCompilePipeline_Basic",
                        "fetch_model": {"resource_path": "examples/assets/mock_model.onnx"},
                    }
                ],
            }
        )
        pipeline = create_pipeline(case.pipeline)
        pipeline_spec = PipelineCompiler().compile(pipeline)

        with tempfile.TemporaryDirectory() as tmp_dir:
            summary = TestEngine(output_root=tmp_dir, debug=False).execute(
                case_spec=case,
                pipeline_spec=pipeline_spec,
                env_profile=EnvProfile.local_default(),
            )
            self.assertEqual(summary.status, "passed")
            remote_path = Path(str(summary.outputs["remote_path"]))
            self.assertTrue(remote_path.exists())
            self.assertEqual(remote_path.name, "model.om")

    def test_local_compile_assert_pipeline_reports_path_exists_and_passed(self) -> None:
        bootstrap()
        case = self._load_case(
            {
                "pipeline": {
                    "name": "LocalCompileAssertPipeline",
                    "assert_remote_path": {"expected_value": True},
                },
                "cases": [
                    {
                        "case_id": "local_compile_assert_case",
                        "name": "LocalCompileAssertPipeline_Basic",
                        "fetch_model": {"resource_path": "examples/assets/mock_model.onnx"},
                    }
                ],
            }
        )
        pipeline = create_pipeline(case.pipeline)
        pipeline_spec = PipelineCompiler().compile(pipeline)

        with tempfile.TemporaryDirectory() as tmp_dir:
            summary = TestEngine(output_root=tmp_dir, debug=False).execute(
                case_spec=case,
                pipeline_spec=pipeline_spec,
                env_profile=EnvProfile.local_default(),
            )
            self.assertEqual(summary.status, "passed")
            self.assertTrue(summary.outputs["path_exists"])
            self.assertTrue(summary.outputs["test_passed"])
            remote_path = Path(str(summary.outputs["remote_path"]))
            self.assertTrue(remote_path.exists())

            run_dirs = list(Path(tmp_dir).iterdir())
            self.assertEqual(len(run_dirs), 1)
            execution_log = run_dirs[0] / "execution.log"
            self.assertTrue(execution_log.exists())
            execution_log_text = execution_log.read_text(encoding="utf-8")
            self.assertIn("[PASS][OUTPUT] 6/6 assert_remote_path (ValueCompare)", execution_log_text)
            self.assertIn("CHECK:", execution_log_text)
            self.assertIn("  - expected_value: True", execution_log_text)
            self.assertIn("  - check_result: True", execution_log_text)
            self.assertIn("O:", execution_log_text)
            self.assertIn("  - test_passed: True", execution_log_text)

    def test_mock_device_pipeline_executes_with_mock_env_profile(self) -> None:
        bootstrap()
        case = self._load_case(
            {
                "pipeline": {"name": "MockDevicePipeline"},
                "cases": [
                    {
                        "case_id": "mock_device_case",
                        "name": "MockDevicePipeline_Basic",
                        "write_message": {"message": "hello mock device"},
                    }
                ],
            }
        )
        pipeline = create_pipeline(case.pipeline)
        pipeline_spec = PipelineCompiler().compile(pipeline)
        env_profile = EnvProfile.from_dict(
            {
                "host": {"mode": "local"},
                "device": {"protocol": "mock", "host": "mock-device", "port": 22, "user": "root"},
                "transport": {"mode": "mock", "size_threshold_mb": 16},
                "metadata": {"profile_name": "mock_device_local"},
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            summary = TestEngine(output_root=tmp_dir, debug=False).execute(
                case_spec=case,
                pipeline_spec=pipeline_spec,
                env_profile=env_profile,
            )
            self.assertEqual(summary.status, "passed")
            self.assertEqual(summary.outputs["device_stdout"], "hello mock device")

    def test_mock_device_roundtrip_pipeline_downloads_device_artifact(self) -> None:
        bootstrap()
        case = self._load_case(
            {
                "pipeline": {"name": "MockDeviceRoundTripPipeline"},
                "cases": [
                    {
                        "case_id": "mock_device_roundtrip_case",
                        "name": "MockDeviceRoundTripPipeline_Basic",
                        "write_message": {"message": "hello roundtrip"},
                    }
                ],
            }
        )
        pipeline = create_pipeline(case.pipeline)
        pipeline_spec = PipelineCompiler().compile(pipeline)
        env_profile = EnvProfile.from_dict(
            {
                "host": {"mode": "local"},
                "device": {"protocol": "mock", "host": "mock-device", "port": 22, "user": "root"},
                "transport": {"mode": "mock", "size_threshold_mb": 16},
                "metadata": {"profile_name": "mock_device_local"},
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            summary = TestEngine(output_root=tmp_dir, debug=False).execute(
                case_spec=case,
                pipeline_spec=pipeline_spec,
                env_profile=env_profile,
            )
            self.assertEqual(summary.status, "passed")
            self.assertEqual(summary.outputs["downloaded_content"], "hello roundtrip")

    def test_mock_device_uppercase_pipeline_transforms_and_asserts_result(self) -> None:
        bootstrap()
        case = self._load_case(
            {
                "pipeline": {"name": "MockDeviceUppercasePipeline"},
                "cases": [
                    {
                        "case_id": "mock_device_uppercase_case",
                        "name": "MockDeviceUppercasePipeline_Basic",
                        "write_message": {"message": "hello ascend"},
                        "compare_result": {"expected_text": "HELLO ASCEND"},
                    }
                ],
            }
        )
        pipeline = create_pipeline(case.pipeline)
        pipeline_spec = PipelineCompiler().compile(pipeline)
        env_profile = EnvProfile.from_dict(
            {
                "host": {"mode": "local"},
                "device": {"protocol": "mock", "host": "mock-device", "port": 22, "user": "root"},
                "transport": {"mode": "mock", "size_threshold_mb": 16},
                "metadata": {"profile_name": "mock_device_local"},
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            summary = TestEngine(output_root=tmp_dir, debug=False).execute(
                case_spec=case,
                pipeline_spec=pipeline_spec,
                env_profile=env_profile,
            )
            self.assertEqual(summary.status, "passed")
            self.assertEqual(summary.outputs["downloaded_content"], "HELLO ASCEND")
            self.assertTrue(summary.outputs["test_passed"])

            run_dirs = list(Path(tmp_dir).iterdir())
            self.assertEqual(len(run_dirs), 1)
            execution_log = run_dirs[0] / "execution.log"
            self.assertTrue(execution_log.exists())
            execution_log_text = execution_log.read_text(encoding="utf-8")
            self.assertIn("[PASS][OUTPUT] 7/7 compare_result (TextEquals)", execution_log_text)
            self.assertIn("CHECK:", execution_log_text)
            self.assertIn("  - expected_text: 'HELLO ASCEND'", execution_log_text)
            self.assertIn("  - check_result: True", execution_log_text)
            self.assertIn("O:", execution_log_text)
            self.assertIn("  - test_passed: True", execution_log_text)

    def test_mock_device_json_pipeline_generates_and_asserts_structured_result(self) -> None:
        bootstrap()
        case = self._load_case(
            {
                "pipeline": {"name": "MockDeviceJsonPipeline"},
                "cases": [
                    {
                        "case_id": "mock_device_json_case",
                        "name": "MockDeviceJsonPipeline_Basic",
                        "write_message": {"message": "hello json"},
                        "assert_json": {
                            "expected_json": {
                                "status": "ok",
                                "message": "HELLO JSON",
                                "metrics.score": 1.0,
                            }
                        },
                    }
                ],
            }
        )
        pipeline = create_pipeline(case.pipeline)
        pipeline_spec = PipelineCompiler().compile(pipeline)
        env_profile = EnvProfile.from_dict(
            {
                "host": {"mode": "local"},
                "device": {"protocol": "mock", "host": "mock-device", "port": 22, "user": "root"},
                "transport": {"mode": "mock", "size_threshold_mb": 16},
                "metadata": {"profile_name": "mock_device_local"},
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            summary = TestEngine(output_root=tmp_dir, debug=False).execute(
                case_spec=case,
                pipeline_spec=pipeline_spec,
                env_profile=env_profile,
            )
            self.assertEqual(summary.status, "passed")
            self.assertEqual(
                summary.outputs["json_data"],
                {"status": "ok", "message": "HELLO JSON", "metrics": {"score": 1.0}},
            )
            self.assertTrue(summary.outputs["test_passed"])

            run_dirs = list(Path(tmp_dir).iterdir())
            self.assertEqual(len(run_dirs), 1)
            execution_log = run_dirs[0] / "execution.log"
            self.assertTrue(execution_log.exists())
            execution_log_text = execution_log.read_text(encoding="utf-8")
            self.assertIn("[PASS][OUTPUT] 7/7 assert_json (JsonObjectAssert)", execution_log_text)
            self.assertIn("CHECK:", execution_log_text)
            self.assertIn("  - expected_json: {'status': 'ok', 'message': 'HELLO JSON', 'metrics.score': 1.0}", execution_log_text)
            self.assertIn("  - check_result: True", execution_log_text)
            self.assertIn("O:", execution_log_text)
            self.assertIn("  - test_passed: True", execution_log_text)


if __name__ == "__main__":
    unittest.main()
