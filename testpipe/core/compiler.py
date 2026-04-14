"""Compile Pipeline DSL objects into PipelineSpec."""

from __future__ import annotations

from testpipe.core.exceptions import PipelineCompileError
from testpipe.core.pipeline import NodeOutputRef, PipelineInputRef
from testpipe.core.registry import get_op_name
from testpipe.spec import EdgeSpec, InputBindingSpec, NodeSpec, PipelineSpec


class PipelineCompiler:
    """Compile authoring-layer pipelines into static specs."""

    def compile(self, pipeline) -> PipelineSpec:
        node_names = [node.name for node in pipeline.nodes]
        if len(node_names) != len(set(node_names)):
            raise PipelineCompileError("duplicate step names in pipeline")

        nodes = []
        edges: list[EdgeSpec] = []
        groups: list[str] = []

        for node in pipeline.nodes:
            spec = getattr(node.op, "spec", None)
            if spec is None:
                raise PipelineCompileError(f"step {node.name} does not expose op spec")
            input_bindings: list[InputBindingSpec] = []
            for input_name, binding in node.input_bindings.items():
                if isinstance(binding, PipelineInputRef):
                    input_bindings.append(
                        InputBindingSpec(
                            input_name=input_name,
                            source_kind="pipeline_input",
                            source_name=binding.port_name,
                        )
                    )
                    continue
                if isinstance(binding, NodeOutputRef):
                    input_bindings.append(
                        InputBindingSpec(
                            input_name=input_name,
                            source_kind="node_output",
                            source_name=binding.node_name,
                            source_port=binding.port_name,
                        )
                    )
                    edges.append(
                        EdgeSpec(
                            source_node=binding.node_name,
                            source_port=binding.port_name,
                            target_node=node.name,
                            target_port=input_name,
                        )
                    )
                    continue
                raise PipelineCompileError(f"unsupported binding for {node.name}.{input_name}: {binding!r}")
            nodes.append(
                NodeSpec(
                    name=node.name,
                    op=get_op_name(node.op),
                    op_version=spec.version,
                    module=node.op.__class__.__module__,
                    attrs=node.op.resolved_attrs(),
                    input_bindings=input_bindings,
                )
            )
            if node.group:
                groups.append(node.group)

        return PipelineSpec(
            name=pipeline.pipeline_name,
            version=getattr(pipeline, "version", "1.0"),
            description=pipeline.description,
            inputs=pipeline.inputs,
            outputs=pipeline.outputs,
            nodes=nodes,
            edges=edges,
            metadata={
                "groups": list(dict.fromkeys(groups)),
            },
        )
