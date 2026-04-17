"""Compile Pipeline DSL objects into PipelineSpec."""

from __future__ import annotations

from testpipe.core.exceptions import PipelineCompileError
from testpipe.core.registry import get_op_name
from testpipe.spec import EdgeSpec, InputBindingSpec, NodeSpec, OutputBindingSpec, PipelineSpec


class PipelineCompiler:
    """Compile authoring-layer pipelines into static specs."""

    def compile(self, pipeline) -> PipelineSpec:
        node_names = [node.name for node in pipeline.nodes]
        if len(node_names) != len(set(node_names)):
            raise PipelineCompileError("duplicate node names in pipeline")

        node_defs = {node.name: node for node in pipeline.nodes}
        pipeline_inputs = {item.name for item in pipeline.inputs}
        nodes = []
        edges = []

        for node in pipeline.nodes:
            spec = getattr(node.op, "spec", None)
            if spec is None:
                raise PipelineCompileError(f"node {node.name} does not expose op spec")
            input_names = {item.name for item in spec.inputs}
            bindings: list[InputBindingSpec] = []
            for target_port, source in node.inputs.items():
                if target_port not in input_names:
                    raise PipelineCompileError(f"node {node.name} does not declare input port: {target_port}")
                if hasattr(source, "input_name"):
                    if source.input_name not in pipeline_inputs:
                        raise PipelineCompileError(f"node {node.name} references unknown pipeline input: {source.input_name}")
                    bindings.append(
                        InputBindingSpec(
                            target_port=target_port,
                            source_type="pipeline_input",
                            source_name=source.input_name,
                        )
                    )
                    continue

                if source.node_name not in node_defs:
                    raise PipelineCompileError(f"node {node.name} references unknown upstream node: {source.node_name}")
                source_spec = getattr(node_defs[source.node_name].op, "spec", None)
                if source_spec is None:
                    raise PipelineCompileError(f"node {source.node_name} does not expose op spec")
                output_names = {item.name for item in source_spec.outputs}
                if source.output_name not in output_names:
                    raise PipelineCompileError(
                        f"node {node.name} references unknown output port: {source.node_name}.{source.output_name}"
                    )
                bindings.append(
                    InputBindingSpec(
                        target_port=target_port,
                        source_type="node_output",
                        source_name=source.node_name,
                        source_port=source.output_name,
                    )
                )
                edges.append(
                    EdgeSpec(
                        source_node=source.node_name,
                        source_port=source.output_name,
                        target_node=node.name,
                        target_port=target_port,
                    )
                )

            nodes.append(
                NodeSpec(
                    name=node.name,
                    op_name=get_op_name(node.op),
                    op_version=spec.version,
                    stage=node.stage,
                    attrs=node.op.resolved_attrs(),
                    input_bindings=bindings,
                )
            )

        output_bindings: list[OutputBindingSpec] = []
        for output in pipeline.output_bindings:
            source = output.source
            if hasattr(source, "input_name"):
                if source.input_name not in pipeline_inputs:
                    raise PipelineCompileError(f"pipeline output {output.name} references unknown input: {source.input_name}")
                output_bindings.append(
                    OutputBindingSpec(
                        output_name=output.name,
                        source_type="pipeline_input",
                        source_name=source.input_name,
                    )
                )
                continue
            if source.node_name not in node_defs:
                raise PipelineCompileError(f"pipeline output {output.name} references unknown node: {source.node_name}")
            source_spec = getattr(node_defs[source.node_name].op, "spec", None)
            if source_spec is None:
                raise PipelineCompileError(f"node {source.node_name} does not expose op spec")
            output_names = {item.name for item in source_spec.outputs}
            if source.output_name not in output_names:
                raise PipelineCompileError(
                    f"pipeline output {output.name} references unknown port: {source.node_name}.{source.output_name}"
                )
            output_bindings.append(
                OutputBindingSpec(
                    output_name=output.name,
                    source_type="node_output",
                    source_name=source.node_name,
                    source_port=source.output_name,
                )
            )

        return PipelineSpec(
            name=pipeline.pipeline_name,
            version=getattr(pipeline, "version", "1.0"),
            description=pipeline.description,
            inputs=pipeline.inputs,
            outputs=pipeline.outputs,
            nodes=nodes,
            edges=edges,
            output_bindings=output_bindings,
            metadata={
                "stages": list(dict.fromkeys(node.stage for node in pipeline.nodes if node.stage)),
            },
        )
