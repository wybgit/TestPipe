"""Built-in MVP pipelines."""

from __future__ import annotations

from testpipe.core import Pipeline, register_pipeline
from testpipe.ops.builtin import EchoOp, EnvCheckOp, ShellCommandOp
from testpipe.spec import PortSpec


@register_pipeline
class SmokePipeline(Pipeline):
    """Minimal smoke pipeline for initial framework validation."""

    def define(self) -> None:
        self.set_inputs(PortSpec(name="message", type="string", description="message to echo"))
        self.set_outputs(PortSpec(name="echoed_message", type="string", description="echo result"))
        self.add_step("env_check", EnvCheckOp())
        self.add_step("host_probe", ShellCommandOp(command="printf smoke-host"))
        self.add_step("echo", EchoOp())
        self.connect("env_check.env_ready", "echo.env_ready")
