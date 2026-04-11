"""Compile Pipeline DSL objects into PipelineSpec."""

from __future__ import annotations

from testpipe.core.exceptions import PipelineCompileError
from testpipe.spec import EdgeSpec, NodeSpec, PipelineSpec


class PipelineCompiler:
    """Compile authoring-layer pipelines into static specs."""

    def compile(self, pipeline) -> PipelineSpec:
        step_names = [step.name for step in pipeline.steps]
        if len(step_names) != len(set(step_names)):
            raise PipelineCompileError("duplicate step names in pipeline")

        nodes = []
        for step in pipeline.steps:
            spec = getattr(step.op, "spec", None)
            if spec is None:
                raise PipelineCompileError(f"step {step.name} does not expose op spec")
            nodes.append(
                NodeSpec(
                    name=step.name,
                    op_type=spec.op_type,
                    op_version=spec.version,
                    stage=step.stage,
                    attrs=step.op.resolved_attrs(),
                )
            )

        edges = [
            EdgeSpec(
                source_node=edge.source_node,
                source_port=edge.source_port,
                target_node=edge.target_node,
                target_port=edge.target_port,
            )
            for edge in pipeline.edges
        ]

        return PipelineSpec(
            name=pipeline.pipeline_name,
            version=getattr(pipeline, "version", "1.0"),
            description=pipeline.description,
            inputs=pipeline.inputs,
            outputs=pipeline.outputs,
            nodes=nodes,
            edges=edges,
            metadata={
                "stages": [step.stage for step in pipeline.steps if step.stage],
            },
        )
