"""ATC-related pipelines."""

from __future__ import annotations

from testpipe.core import Pipeline, register_pipeline
from testpipe.ops.asserts import PathExistsOp, ValueCompareOp
from testpipe.ops.atc import ATCCompileOp
from testpipe.ops.builtin import EnvCheckOp
from testpipe.ops.resource import ResourceFetchOp
from testpipe.ops.transfer import TransferOp
from testpipe.spec import PortSpec


@register_pipeline
class LocalCompilePipeline(Pipeline):
    """Local resource fetch, compile, and transfer pipeline for MVP validation."""

    def define(self) -> None:
        self.set_inputs(PortSpec(name="resource_path", type="artifact:path", description="source model path"))
        self.set_outputs(PortSpec(name="remote_path", type="artifact:path", description="staged transferred model"))

        self.add_node("env_check", EnvCheckOp())
        fetch_model = self.add_node(
            "fetch_model",
            ResourceFetchOp(),
            inputs={"resource_path": self.input("resource_path")},
        )
        compile_model = self.add_node(
            "compile_model",
            ATCCompileOp(output_name="model.om"),
            inputs={"model_path": fetch_model.output("model_path")},
        )
        self.add_node(
            "transfer_model",
            TransferOp(target_dir="device"),
            inputs={"local_path": compile_model.output("om_path")},
        )


@register_pipeline
class LocalCompileAssertPipeline(Pipeline):
    """Fetch, compile, and transfer a model, then assert the transferred artifact exists."""

    def define(self) -> None:
        self.set_inputs(PortSpec(name="resource_path", type="artifact:path", description="source model path"))
        self.set_outputs(
            PortSpec(name="remote_path", type="artifact:path", description="staged transferred model"),
            PortSpec(name="path_exists", type="bool", description="whether the transferred artifact exists"),
            PortSpec(name="test_passed", type="bool", description="assertion result"),
        )

        self.add_node("env_check", EnvCheckOp())
        fetch_model = self.add_node(
            "fetch_model",
            ResourceFetchOp(),
            inputs={"resource_path": self.input("resource_path")},
        )
        compile_model = self.add_node(
            "compile_model",
            ATCCompileOp(output_name="model.om"),
            inputs={"model_path": fetch_model.output("model_path")},
        )
        transfer_model = self.add_node(
            "transfer_model",
            TransferOp(target_dir="device"),
            inputs={"local_path": compile_model.output("om_path")},
        )
        check_remote_path = self.add_node(
            "check_remote_path",
            PathExistsOp(),
            inputs={"target_path": transfer_model.output("remote_path")},
        )
        self.add_node(
            "assert_remote_path",
            ValueCompareOp(operator="eq", expected_value=True),
            inputs={"actual_value": check_remote_path.output("path_exists")},
        )


@register_pipeline
class OnnxGitAtcPipeline(Pipeline):
    """Fetch an ONNX model from git resources and compile it into OM through ATC."""

    def define(self) -> None:
        self.set_inputs(
            PortSpec(name="resource_ref", type="object", description="git-backed resource reference"),
            PortSpec(name="soc_version", type="string", description="target soc version"),
            PortSpec(name="atc_options", type="object", required=False, description="extra atc options"),
            PortSpec(name="output_name", type="string", required=False, description="output om file name"),
            PortSpec(name="env_script", type="string", required=False, description="cann env script"),
        )
        self.set_outputs(
            PortSpec(name="resolved_commit", type="string", description="resolved git commit"),
            PortSpec(name="model_path", type="artifact:path", description="resolved onnx model path"),
            PortSpec(name="om_path", type="artifact:path", description="compiled om artifact"),
            PortSpec(name="path_exists", type="bool", description="compiled om existence"),
            PortSpec(name="test_passed", type="bool", description="compile assertion result"),
        )

        self.add_node("env_check", EnvCheckOp())
        fetch_model = self.add_node(
            "fetch_model",
            ResourceFetchOp(),
            inputs={"resource_ref": self.input("resource_ref")},
        )
        compile_model = self.add_node(
            "compile_model",
            ATCCompileOp(output_name="model.om", timeout=600),
            inputs={
                "model_path": fetch_model.output("model_path"),
                "soc_version": self.input("soc_version"),
                "atc_options": self.input("atc_options"),
                "output_name": self.input("output_name"),
                "env_script": self.input("env_script"),
            },
        )
        check_om_exists = self.add_node(
            "check_om_exists",
            PathExistsOp(),
            inputs={"target_path": compile_model.output("om_path")},
        )
        self.add_node(
            "assert_om_exists",
            ValueCompareOp(operator="eq", expected_value=True),
            inputs={"actual_value": check_om_exists.output("path_exists")},
        )
