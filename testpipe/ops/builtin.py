"""Built-in basic and system operators."""

from __future__ import annotations

from pathlib import Path

from testpipe.core import TestOp, register_op
from testpipe.spec import OpSpec, PortSpec

_DEFAULT_CANN_ENV_SCRIPT = "/home/wyb/Ascend/cann-8.5.0/set_env.sh"


@register_op
class EnvCheckOp(TestOp):
    """Validate that the configured CANN environment script exists."""

    spec = OpSpec(
        version="1.0",
        description="Validate that the configured CANN environment script exists",
        inputs=[
            PortSpec(name="env_script", type="string", required=False, description="cann environment script path"),
        ],
        outputs=[
            PortSpec(
                name="env_ready",
                type="bool",
                description="environment readiness flag",
                expose=False,
            ),
            PortSpec(
                name="env_script",
                type="string",
                description="validated cann environment script path",
                expose=False,
            ),
        ],
        attrs=[],
    )

    def execute(self, step_context) -> dict[str, bool | str]:
        env_script = Path(str(step_context.inputs.get("env_script", _DEFAULT_CANN_ENV_SCRIPT))).expanduser().resolve()
        if not env_script.exists():
            raise RuntimeError(f"cann env script not found: {env_script}")
        return {
            "env_ready": True,
            "env_script": str(env_script),
        }
