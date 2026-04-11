"""Built-in operators for the initial MVP."""

from __future__ import annotations

from pathlib import Path

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
class ResourceFetchOp(TestOp):
    """Materialize a local resource into the run workspace."""

    spec = OpSpec(
        op_type="ResourceFetch",
        version="1.0",
        category="resource",
        description="Fetch a local resource into the execution workspace",
        inputs=[PortSpec(name="resource_path", type="artifact:path", description="source resource path")],
        outputs=[
            PortSpec(
                name="model_path",
                type="artifact:path",
                description="workspace-local model path",
                expose=False,
            )
        ],
        attrs=[],
    )

    def execute(self, step_context) -> dict[str, str]:
        source = Path(str(step_context.inputs.require("resource_path"))).expanduser().resolve()
        if not source.exists():
            raise RuntimeError(f"resource not found: {source}")

        destination = Path(step_context.step_dir) / source.name
        step_context.host.exec(["cp", str(source), str(destination)])
        stable_path = step_context.artifacts.add_file(
            "fetched_resource",
            str(destination),
            step_name=step_context.node_name,
        )
        return {"model_path": stable_path}


@register_op
class ATCCompileOp(TestOp):
    """Compile a fetched model into a mock OM artifact for local MVP runs."""

    spec = OpSpec(
        op_type="ATCCompile",
        version="1.0",
        category="compile",
        description="Compile a model into a local OM artifact",
        inputs=[PortSpec(name="model_path", type="artifact:path", description="workspace model path")],
        outputs=[PortSpec(name="om_path", type="artifact:path", description="compiled om path")],
        attrs=[
            AttrSpec(name="output_name", type="string", required=False, default="compiled_model.om", description="compiled output filename"),
            AttrSpec(name="timeout", type="int", required=False, default=30, description="command timeout"),
        ],
    )

    def execute(self, step_context) -> dict[str, str]:
        source = Path(str(step_context.inputs.require("model_path"))).resolve()
        if not source.exists():
            raise RuntimeError(f"model not found: {source}")

        destination = Path(step_context.step_dir) / str(step_context.attrs.get("output_name", "compiled_model.om"))
        step_context.host.exec(["cp", str(source), str(destination)], timeout=step_context.attrs.get("timeout", 30))
        stable_path = step_context.artifacts.add_file(
            "compiled_model",
            str(destination),
            step_name=step_context.node_name,
        )
        return {"om_path": stable_path}


@register_op
class TransferOp(TestOp):
    """Transfer an artifact into a mock device staging directory."""

    spec = OpSpec(
        op_type="Transfer",
        version="1.0",
        category="transfer",
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
