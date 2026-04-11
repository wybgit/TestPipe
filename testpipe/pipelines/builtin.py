"""Built-in MVP pipelines."""

from __future__ import annotations

from testpipe.core import Pipeline, register_pipeline
from testpipe.ops.builtin import ATCCompileOp, EchoOp, EnvCheckOp, ResourceFetchOp, ShellCommandOp, TransferOp
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
