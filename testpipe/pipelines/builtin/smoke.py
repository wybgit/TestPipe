"""Basic built-in pipelines."""

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

        env_check = self.add_node("env_check", EnvCheckOp())
        self.add_node("host_probe", ShellCommandOp(command="printf smoke-host"))
        self.add_node(
            "echo",
            EchoOp(),
            inputs={
                "message": self.input("message"),
                "env_ready": env_check.output("env_ready"),
            },
        )
