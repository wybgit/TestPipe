"""Built-in basic and system operators."""

from __future__ import annotations

import json
from pathlib import Path

from testpipe.core import TestOp, register_op
from testpipe.spec import AttrSpec, OpSpec, PortSpec


@register_op
class EnvCheckOp(TestOp):
    """Minimal environment check operator."""

    spec = OpSpec(
        version="1.0",
        description="Validate the local execution environment",
        inputs=[],
        outputs=[
            PortSpec(
                name="env_ready",
                type="bool",
                description="environment readiness flag",
                expose=False,
            )
        ],
        attrs=[],
    )

    def execute(self, step_context) -> dict[str, bool]:
        return {"env_ready": True}


@register_op
class EchoOp(TestOp):
    """Return the input message once environment is ready."""

    spec = OpSpec(
        version="1.0",
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
        version="1.0",
        description="Execute a shell command through ActionRunner",
        inputs=[],
        outputs=[
            PortSpec(
                name="stdout",
                type="string",
                description="captured stdout",
                expose=False,
            )
        ],
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


@register_op
class WriteTextArtifactOp(TestOp):
    """Materialize plain text content as a run artifact."""

    spec = OpSpec(
        version="1.0",
        description="Write input text to an artifact file",
        inputs=[
            PortSpec(name="content", type="string", required=False, description="text content"),
            PortSpec(name="message", type="string", required=False, description="legacy message alias"),
        ],
        outputs=[PortSpec(name="file_path", type="artifact:path", description="written file path", expose=False)],
        attrs=[
            AttrSpec(name="filename", type="string", required=False, default="payload.txt", description="artifact filename"),
        ],
    )

    def execute(self, step_context) -> dict[str, str]:
        raw_content = step_context.inputs.get("content", step_context.inputs.get("message"))
        if raw_content is None:
            raise KeyError("missing required key: content")
        content = str(raw_content)
        filename = str(step_context.attrs.get("filename", "payload.txt"))
        output_path = Path(step_context.step_dir) / filename
        output_path.write_text(content, encoding="utf-8")
        stable_path = step_context.artifacts.add_file("text_artifact", str(output_path), step_name=step_context.node_name)
        return {"file_path": stable_path}


@register_op
class ReadTextArtifactOp(TestOp):
    """Read plain text from a local artifact file."""

    spec = OpSpec(
        version="1.0",
        description="Read text content from a local artifact path",
        inputs=[PortSpec(name="file_path", type="artifact:path", description="artifact path to read")],
        outputs=[
            PortSpec(name="content", type="string", description="text content"),
            PortSpec(name="downloaded_content", type="string", description="downloaded text content"),
        ],
        attrs=[],
    )

    def execute(self, step_context) -> dict[str, str]:
        source = Path(str(step_context.inputs.require("file_path"))).resolve()
        if not source.exists():
            raise RuntimeError(f"artifact not found: {source}")
        content = source.read_text(encoding="utf-8")
        return {
            "content": content,
            "downloaded_content": content,
        }


@register_op
class ReadJsonArtifactOp(TestOp):
    """Read JSON content from a local artifact file."""

    spec = OpSpec(
        version="1.0",
        description="Read JSON content from a local artifact path",
        inputs=[PortSpec(name="file_path", type="artifact:path", description="artifact path to read")],
        outputs=[
            PortSpec(name="json_data", type="object", description="decoded JSON object", expose=False),
        ],
        attrs=[],
    )

    def execute(self, step_context) -> dict[str, object]:
        source = Path(str(step_context.inputs.require("file_path"))).resolve()
        if not source.exists():
            raise RuntimeError(f"artifact not found: {source}")
        return {"json_data": json.loads(source.read_text(encoding="utf-8"))}


@register_op
class TransferOp(TestOp):
    """Transfer an artifact into a mock device staging directory."""

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
