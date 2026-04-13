"""Built-in MVP pipelines."""

from __future__ import annotations

from testpipe.core import Pipeline, register_pipeline
from testpipe.ops.builtin import (
    ATCCompileOp,
    DeviceCommandOp,
    EchoOp,
    EnvCheckOp,
    JsonObjectAssertOp,
    PathExistsOp,
    ReadJsonArtifactOp,
    ReadTextArtifactOp,
    ResourceFetchOp,
    ShellCommandOp,
    TextEqualsOp,
    TransferOp,
    TransferGetOp,
    TransferPutOp,
    ValueCompareOp,
    WriteTextArtifactOp,
)
from testpipe.spec import PortSpec


@register_pipeline
class SmokePipeline(Pipeline):
    """Minimal smoke pipeline for initial framework validation."""

    def define(self) -> None:
        self.set_inputs(PortSpec(name="message", type="string", description="message to echo"))
        self.set_outputs(PortSpec(name="echoed_message", type="string", description="echo result"))
        self.set_stage("prepare")
        self.add_step("env_check", EnvCheckOp())
        self.add_step("host_probe", ShellCommandOp(command="printf smoke-host"))
        self.set_stage("execute")
        self.add_step("echo", EchoOp())
        self.connect("env_check.env_ready", "echo.env_ready")


@register_pipeline
class LocalCompilePipeline(Pipeline):
    """Local resource fetch, compile, and transfer pipeline for MVP validation."""

    def define(self) -> None:
        self.set_inputs(PortSpec(name="resource_path", type="artifact:path", description="source model path"))
        self.set_outputs(PortSpec(name="remote_path", type="artifact:path", description="staged transferred model"))

        self.set_stage("prepare")
        self.add_step("env_check", EnvCheckOp())
        self.add_step("fetch_model", ResourceFetchOp())

        self.set_stage("compile")
        self.add_step("compile_model", ATCCompileOp(output_name="model.om"))

        self.set_stage("transfer")
        self.add_step("transfer_model", TransferOp(target_dir="device"))

        self.connect("fetch_model.model_path", "compile_model.model_path")
        self.connect("compile_model.om_path", "transfer_model.local_path")


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

        self.set_stage("prepare")
        self.add_step("env_check", EnvCheckOp())
        self.add_step("fetch_model", ResourceFetchOp())

        self.set_stage("compile")
        self.add_step("compile_model", ATCCompileOp(output_name="model.om"))

        self.set_stage("transfer")
        self.add_step("transfer_model", TransferOp(target_dir="device"))

        self.set_stage("assert")
        self.add_step("check_remote_path", PathExistsOp())
        self.add_step("assert_remote_path", ValueCompareOp(operator="eq", expected_value=True))

        self.connect("fetch_model.model_path", "compile_model.model_path")
        self.connect("compile_model.om_path", "transfer_model.local_path")
        self.connect("transfer_model.remote_path", "check_remote_path.target_path")
        self.connect("check_remote_path.path_exists", "assert_remote_path.actual_value")


@register_pipeline
class MockDevicePipeline(Pipeline):
    """Write a text artifact, upload it to a mock device, and read it back."""

    def define(self) -> None:
        self.set_inputs(PortSpec(name="message", type="string", description="text to send to mock device"))
        self.set_outputs(PortSpec(name="device_stdout", type="string", description="text read back from mock device"))

        self.set_stage("prepare")
        self.add_step("env_check", EnvCheckOp())
        self.add_step("write_message", WriteTextArtifactOp(filename="message.txt"))

        self.set_stage("transfer")
        self.add_step("upload_message", TransferPutOp(remote_path="/inputs/message.txt"))

        self.set_stage("execute")
        self.add_step("read_message", DeviceCommandOp(command="cat inputs/message.txt"))

        self.connect("write_message.file_path", "upload_message.local_path")


@register_pipeline
class MockDeviceRoundTripPipeline(Pipeline):
    """Upload input text to mock device, materialize a device-side output file, download it, and read it back."""

    def define(self) -> None:
        self.set_inputs(PortSpec(name="message", type="string", description="text to round-trip through mock device"))
        self.set_outputs(PortSpec(name="downloaded_content", type="string", description="content downloaded back from device"))

        self.set_stage("prepare")
        self.add_step("env_check", EnvCheckOp())
        self.add_step("write_message", WriteTextArtifactOp(filename="message.txt"))

        self.set_stage("transfer")
        self.add_step("upload_message", TransferPutOp(remote_path="/inputs/message.txt"))

        self.set_stage("device_execute")
        self.add_step(
            "produce_device_output",
            DeviceCommandOp(command="sh -lc 'mkdir -p outputs && cat inputs/message.txt > outputs/result.txt'"),
        )

        self.set_stage("collect")
        self.add_step("download_result", TransferGetOp(remote_path="/outputs/result.txt", local_name="result.txt"))
        self.add_step("read_result", ReadTextArtifactOp())

        self.connect("write_message.file_path", "upload_message.local_path")
        self.connect("download_result.local_path", "read_result.file_path")


@register_pipeline
class MockDeviceUppercasePipeline(Pipeline):
    """Upload text to mock device, transform it on device, download the result, and verify business output."""

    def define(self) -> None:
        self.set_inputs(
            PortSpec(name="message", type="string", description="text sent to the mock device"),
            PortSpec(name="expected_text", type="string", description="expected transformed output"),
        )
        self.set_outputs(
            PortSpec(name="downloaded_content", type="string", description="device-generated output content"),
            PortSpec(name="test_passed", type="bool", description="business check result"),
        )

        self.set_stage("prepare")
        self.add_step("env_check", EnvCheckOp())
        self.add_step("write_message", WriteTextArtifactOp(filename="message.txt"))

        self.set_stage("transfer")
        self.add_step("upload_message", TransferPutOp(remote_path="/inputs/message.txt"))

        self.set_stage("device_execute")
        self.add_step(
            "uppercase_message",
            DeviceCommandOp(
                command="sh -lc \"mkdir -p outputs && tr '[:lower:]' '[:upper:]' < inputs/message.txt > outputs/result.txt\""
            ),
        )

        self.set_stage("collect")
        self.add_step("download_result", TransferGetOp(remote_path="/outputs/result.txt", local_name="uppercase_result.txt"))
        self.add_step("read_result", ReadTextArtifactOp())

        self.set_stage("assert")
        self.add_step("compare_result", TextEqualsOp(strip=True))

        self.connect("write_message.file_path", "upload_message.local_path")
        self.connect("download_result.local_path", "read_result.file_path")
        self.connect("read_result.content", "compare_result.actual_text")


@register_pipeline
class MockDeviceJsonPipeline(Pipeline):
    """Upload text to mock device, generate a JSON result on device, download it, and assert structured fields."""

    def define(self) -> None:
        self.set_inputs(
            PortSpec(name="message", type="string", description="text sent to the mock device"),
            PortSpec(name="expected_json", type="object", description="expected JSON field values"),
        )
        self.set_outputs(
            PortSpec(name="json_data", type="object", description="downloaded JSON result"),
            PortSpec(name="test_passed", type="bool", description="structured assertion result"),
        )

        self.set_stage("prepare")
        self.add_step("env_check", EnvCheckOp())
        self.add_step("write_message", WriteTextArtifactOp(filename="message.txt"))

        self.set_stage("transfer")
        self.add_step("upload_message", TransferPutOp(remote_path="/inputs/message.txt"))

        self.set_stage("device_execute")
        self.add_step(
            "build_json_result",
            DeviceCommandOp(
                command="""python3 - <<'PY'
import json
from pathlib import Path

message_path = Path("inputs/message.txt")
message = message_path.read_text(encoding="utf-8").strip()
result = {
    "status": "ok",
    "message": message.upper(),
    "metrics": {"score": 1.0},
}
output_dir = Path("outputs")
output_dir.mkdir(parents=True, exist_ok=True)
(output_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
PY""",
            ),
        )

        self.set_stage("collect")
        self.add_step("download_result", TransferGetOp(remote_path="/outputs/result.json", local_name="result.json"))
        self.add_step("read_result", ReadJsonArtifactOp())

        self.set_stage("assert")
        self.add_step("assert_json", JsonObjectAssertOp())

        self.connect("write_message.file_path", "upload_message.local_path")
        self.connect("download_result.local_path", "read_result.file_path")
        self.connect("read_result.json_data", "assert_json.json_data")


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

        self.set_stage("prepare")
        self.add_step("env_check", EnvCheckOp())
        self.add_step("fetch_model", ResourceFetchOp())

        self.set_stage("compile")
        self.add_step("compile_model", ATCCompileOp(output_name="model.om", timeout=600))

        self.set_stage("assert")
        self.add_step("check_om_exists", PathExistsOp())
        self.add_step("assert_om_exists", ValueCompareOp(operator="eq", expected_value=True))

        self.connect("fetch_model.model_path", "compile_model.model_path")
        self.connect("compile_model.om_path", "check_om_exists.target_path")
        self.connect("check_om_exists.path_exists", "assert_om_exists.actual_value")
