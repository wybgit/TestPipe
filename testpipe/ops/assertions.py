"""Assertion operators."""

from __future__ import annotations

from pathlib import Path

from testpipe.core import TestOp, register_op
from testpipe.spec import OpSpec, PortSpec


@register_op
class PathExistsOp(TestOp):
    """Check whether a local path exists."""

    spec = OpSpec(
        version="1.0",
        description="Check whether a local file or directory exists",
        inputs=[PortSpec(name="target_path", type="artifact:path", description="path to inspect")],
        outputs=[
            PortSpec(name="path_exists", type="bool", description="path existence result"),
            PortSpec(name="checked_path", type="artifact:path", description="normalized checked path"),
        ],
        attrs=[],
    )

    def execute(self, step_context) -> dict[str, bool | str]:
        target_path = Path(str(step_context.inputs.require("target_path"))).expanduser().resolve()
        return {
            "path_exists": target_path.exists(),
            "checked_path": str(target_path),
        }
