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
    def test_smoke_pipeline_executes_in_normal_mode(self) -> None:
        bootstrap()
        case = TestCaseLoader().load("examples/testcases/smoke.yaml")
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
        case = TestCaseLoader().load("examples/testcases/smoke.yaml")
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


if __name__ == "__main__":
    unittest.main()
