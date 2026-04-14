"""Transfer operators."""

from __future__ import annotations

from pathlib import Path

from testpipe.core import TestOp, register_op
from testpipe.spec import AttrSpec, OpSpec, PortSpec


@register_op
class TransferOp(TestOp):
    """Transfer an artifact into a local staging directory."""

    spec = OpSpec(
        version="1.0",
        description="Transfer a local artifact into a staged target directory",
        inputs=[PortSpec(name="local_path", type="artifact:path", description="local artifact path")],
        outputs=[PortSpec(name="remote_path", type="artifact:path", description="staged remote path")],
        attrs=[
            AttrSpec(name="target_dir", type="string", required=False, default="device", description="staging directory name"),
            AttrSpec(name="timeout", type="int", required=False, default=30, description="command timeout"),
        ],
    )

    def execute(self, step_context) -> dict[str, str]:
        source = Path(str(step_context.inputs.require("local_path"))).resolve()
        if not source.exists():
            raise RuntimeError(f"local artifact not found: {source}")

        target_dir = Path(step_context.artifacts.root_dir) / str(step_context.attrs.get("target_dir", "device"))
        target_dir.mkdir(parents=True, exist_ok=True)
        destination = target_dir / source.name
        step_context.host.exec(["cp", str(source), str(destination)], timeout=step_context.attrs.get("timeout", 30))
        return {"remote_path": str(destination)}


@register_op
class TransferPutOp(TestOp):
    """Upload an artifact to the configured device through TransferExecutor."""

    spec = OpSpec(
        version="1.0",
        description="Transfer a local artifact to the configured device path",
        inputs=[PortSpec(name="local_path", type="artifact:path", description="local artifact path")],
        outputs=[PortSpec(name="remote_path", type="artifact:path", description="device-side artifact path")],
        attrs=[
            AttrSpec(name="remote_path", type="string", required=True, description="destination path on device"),
        ],
    )

    def execute(self, step_context) -> dict[str, str]:
        if step_context.transfer is None:
            raise RuntimeError("transfer executor is not configured")
        remote_path = step_context.transfer.put(
            str(step_context.inputs.require("local_path")),
            str(step_context.attrs.require("remote_path")),
        )
        return {"remote_path": remote_path}


@register_op
class TransferGetOp(TestOp):
    """Download an artifact from the configured device through TransferExecutor."""

    spec = OpSpec(
        version="1.0",
        description="Transfer a remote device artifact back to the local workspace",
        inputs=[],
        outputs=[PortSpec(name="local_path", type="artifact:path", description="downloaded local artifact path", expose=False)],
        attrs=[
            AttrSpec(name="remote_path", type="string", required=True, description="source path on device"),
            AttrSpec(name="local_name", type="string", required=False, default="downloaded.txt", description="local output filename"),
        ],
    )

    def execute(self, step_context) -> dict[str, str]:
        if step_context.transfer is None:
            raise RuntimeError("transfer executor is not configured")
        local_name = str(step_context.attrs.get("local_name", "downloaded.txt"))
        local_path = Path(step_context.step_dir) / local_name
        downloaded_path = step_context.transfer.get(
            str(step_context.attrs.require("remote_path")),
            str(local_path),
        )
        stable_path = step_context.artifacts.add_file("downloaded_artifact", downloaded_path, step_name=step_context.node_name)
        return {"local_path": stable_path}
