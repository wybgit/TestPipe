"""ATC-oriented pipelines."""

from __future__ import annotations

from testpipe.core import Pipeline, register_pipeline
from testpipe.ops.assertions import PathExistsOp
from testpipe.ops.atc import ATCCompileOp
from testpipe.ops.resource import ResourceFetchOp


@register_pipeline
class OnnxGitAtcPipeline(Pipeline):
    """Fetch an ONNX model from git resources and compile it into OM through ATC."""

    def define(self) -> None:
        self.set_stage("prepare")
        fetch_model = self.add_node("fetchModelNode", ResourceFetchOp())

        self.set_stage("compile")
        compile_model = self.add_node(
            "compileModelNode",
            ATCCompileOp(output_name="model.om", timeout=600),
            inputs={"model_path": fetch_model.output("model_path")},
        )

        self.set_stage("assert")
        check_om_exists = self.add_node(
            "checkOmExistsNode",
            PathExistsOp(),
            inputs={"target_path": compile_model.output("om_path")},
        )
        self.add_output("model_path", fetch_model.output("model_path"), type="artifact:path", description="resolved onnx model path")
        self.add_output("om_path", compile_model.output("om_path"), type="artifact:path", description="compiled om artifact")
        self.add_output("path_exists", check_om_exists.output("path_exists"), type="bool", description="compiled om existence")
