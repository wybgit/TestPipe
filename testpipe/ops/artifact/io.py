"""Artifact materialization and reading operators."""

from __future__ import annotations

import json
from pathlib import Path

from testpipe.core import TestOp, register_op
from testpipe.spec import AttrSpec, OpSpec, PortSpec


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
