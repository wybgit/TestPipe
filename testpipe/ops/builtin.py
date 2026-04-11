"""Built-in operators for the initial MVP."""

from __future__ import annotations

from testpipe.core import TestOp, register_op
from testpipe.spec import AttrSpec, OpSpec, PortSpec


@register_op
class EnvCheckOp(TestOp):
    """Minimal environment check operator."""

    spec = OpSpec(
        op_type="EnvCheck",
        version="1.0",
        category="infra",
        description="Validate the local execution environment",
        inputs=[],
        outputs=[PortSpec(name="env_ready", type="bool", description="environment readiness flag")],
        attrs=[],
    )

    def execute(self, step_context) -> dict[str, bool]:
        return {"env_ready": True}


@register_op
class EchoOp(TestOp):
    """Return the input message once environment is ready."""

    spec = OpSpec(
        op_type="Echo",
        version="1.0",
        category="utility",
        description="Echo a message from pipeline input",
        inputs=[
            PortSpec(name="message", type="string", description="input message"),
            PortSpec(name="env_ready", type="bool", required=False, description="optional env check result"),
        ],
        outputs=[PortSpec(name="echoed_message", type="string", description="echoed message")],
        attrs=[],
    )

    def execute(self, step_context) -> dict[str, str]:
        env_ready = step_context.inputs.get("env_ready", True)
        if not env_ready:
            raise RuntimeError("environment is not ready")
        return {"echoed_message": str(step_context.inputs.require("message"))}


@register_op
class ShellCommandOp(TestOp):
    """Execute a shell command on the host and return stdout."""

    spec = OpSpec(
        op_type="ShellCommand",
        version="1.0",
        category="host",
        description="Execute a shell command through ActionRunner",
        inputs=[],
        outputs=[PortSpec(name="stdout", type="string", description="captured stdout")],
        attrs=[
            AttrSpec(name="command", type="string", required=True, description="shell command to execute"),
            AttrSpec(name="timeout", type="int", required=False, default=30, description="execution timeout"),
        ],
    )

    def execute(self, step_context) -> dict[str, str]:
        result = step_context.host.exec(
            step_context.attrs.require("command"),
            timeout=step_context.attrs.get("timeout", 30),
        )
        return {"stdout": result.stdout.strip()}
