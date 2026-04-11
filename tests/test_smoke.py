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
    def test_smoke_pipeline_executes(self) -> None:
        bootstrap()
        case = TestCaseLoader().load("examples/testcases/smoke.yaml")
        pipeline = create_pipeline(case.pipeline)
        pipeline_spec = PipelineCompiler().compile(pipeline)

        with tempfile.TemporaryDirectory() as tmp_dir:
            summary = TestEngine(output_root=tmp_dir).execute(
                case_spec=case,
                pipeline_spec=pipeline_spec,
                env_profile=EnvProfile.local_default(),
            )
            self.assertEqual(summary.status, "passed")
            self.assertEqual(summary.outputs["echoed_message"], "hello testpipe")

            run_dirs = list(Path(tmp_dir).iterdir())
            self.assertEqual(len(run_dirs), 1)
            summary_path = run_dirs[0] / "summary.json"
            self.assertTrue(summary_path.exists())
            self.assertEqual(json.loads(summary_path.read_text(encoding="utf-8"))["status"], "passed")


if __name__ == "__main__":
    unittest.main()
