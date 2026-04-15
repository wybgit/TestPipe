"""ATC compile operators."""

from __future__ import annotations

import shlex
from pathlib import Path

from testpipe.core import TestOp, register_op
from testpipe.spec import AttrSpec, OpSpec, PortSpec

_DEFAULT_CANN_ENV_SCRIPT = "/home/wyb/Ascend/cann-8.5.0/set_env.sh"


@register_op
class ATCCompileOp(TestOp):
    """Compile a fetched model into an OM artifact, falling back to mock copy for legacy pipelines."""

    spec = OpSpec(
        version="1.0",
        description="Compile a model into a local OM artifact",
        inputs=[PortSpec(name="model_path", type="artifact:path", description="workspace model path")],
        outputs=[PortSpec(name="om_path", type="artifact:path", description="compiled om path")],
        attrs=[
            AttrSpec(name="output_name", type="string", required=False, default="compiled_model.om", description="compiled output filename"),
            AttrSpec(name="soc_version", type="string", required=False, default="Ascend310P3", description="target soc version"),
            AttrSpec(name="atc_options", type="object", required=False, default=None, description="extra atc options"),
            AttrSpec(name="env_script", type="string", required=False, default=_DEFAULT_CANN_ENV_SCRIPT, description="cann env script"),
            AttrSpec(name="timeout", type="int", required=False, default=30, description="command timeout"),
            AttrSpec(name="framework", type="int", required=False, default=5, description="atc framework id"),
        ],
    )

    def execute(self, step_context) -> dict[str, str]:
        source = Path(str(step_context.inputs.require("model_path"))).resolve()
        if not source.exists():
            raise RuntimeError(f"model not found: {source}")

        output_name = str(step_context.attrs.get("output_name", "compiled_model.om"))
        timeout = step_context.attrs.get("timeout", 30)
        soc_version = step_context.attrs.get("soc_version")
        if soc_version in {None, ""}:
            destination = Path(step_context.step_dir) / output_name
            step_context.host.exec(["cp", str(source), str(destination)], timeout=timeout)
        else:
            env_script = str(step_context.attrs.get("env_script", _DEFAULT_CANN_ENV_SCRIPT))
            if not Path(env_script).expanduser().exists():
                raise RuntimeError(f"cann env script not found: {env_script}")
            output_prefix = self._output_prefix(Path(step_context.step_dir), output_name)
            compile_command = self._build_atc_command(
                model_path=source,
                output_prefix=output_prefix,
                framework=int(step_context.attrs.get("framework", 5)),
                soc_version=str(soc_version),
                atc_options=step_context.attrs.get("atc_options"),
            )
            command = f"source {shlex.quote(env_script)} && {' '.join(shlex.quote(part) for part in compile_command)}"
            step_context.host.exec(["bash", "-lc", command], timeout=timeout)
            destination = Path(f"{output_prefix}.om")
            if not destination.exists():
                raise RuntimeError(f"atc did not produce expected om file: {destination}")

        stable_path = step_context.artifacts.add_file(
            "compiled_model",
            str(destination),
            step_name=step_context.node_name,
        )
        return {"om_path": stable_path}

    def _output_prefix(self, step_dir: Path, output_name: str) -> Path:
        output_path = step_dir / output_name
        if output_path.suffix == ".om":
            return output_path.with_suffix("")
        return output_path

    def _build_atc_command(
        self,
        *,
        model_path: Path,
        output_prefix: Path,
        framework: int,
        soc_version: str,
        atc_options: object,
    ) -> list[str]:
        command = [
            "atc",
            f"--model={model_path}",
            f"--framework={framework}",
            f"--output={output_prefix}",
            f"--soc_version={soc_version}",
        ]
        command.extend(self._render_extra_atc_args(atc_options))
        return command

    def _render_extra_atc_args(self, atc_options: object) -> list[str]:
        if atc_options is None:
            return []
        if not isinstance(atc_options, dict):
            raise RuntimeError("atc_options must be an object")
        reserved = {"model", "framework", "output", "soc_version"}
        rendered: list[str] = []
        for key in sorted(atc_options.keys()):
            if key in reserved:
                raise RuntimeError(f"atc_options cannot override reserved argument: {key}")
            value = atc_options[key]
            if isinstance(value, bool):
                value = "true" if value else "false"
            rendered.append(f"--{key}={value}")
        return rendered
