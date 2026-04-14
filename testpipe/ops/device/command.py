"""Device-side execution operators."""

from __future__ import annotations

from testpipe.core import TestOp, register_op
from testpipe.spec import AttrSpec, OpSpec, PortSpec


@register_op
class DeviceCommandOp(TestOp):
    """Execute a command on the configured device."""

    spec = OpSpec(
        version="1.0",
        description="Execute a shell command on the configured device executor",
        inputs=[],
        outputs=[PortSpec(name="device_stdout", type="string", description="captured device stdout")],
        attrs=[
            AttrSpec(name="command", type="string", required=True, description="shell command to execute on device"),
            AttrSpec(name="timeout", type="int", required=False, default=30, description="execution timeout"),
        ],
    )

    def execute(self, step_context) -> dict[str, str]:
        if step_context.device is None:
            raise RuntimeError("device executor is not configured")
        result = step_context.device.exec(
            str(step_context.attrs.require("command")),
            timeout=step_context.attrs.get("timeout", 30),
        )
        return {"device_stdout": result.stdout.strip()}
