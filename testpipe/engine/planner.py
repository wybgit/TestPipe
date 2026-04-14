"""Execution planning and topological sorting."""

from __future__ import annotations

from dataclasses import dataclass

from testpipe.core.exceptions import ValidationError


@dataclass(slots=True)
class ExecutionStep:
    index: int
    node_name: str
    op_name: str
    depends_on: list[str]


class ExecutionPlanner:
    """Build ordered execution steps from a PipelineSpec."""

    def build(self, pipeline_spec) -> list[ExecutionStep]:
        node_names = [node.name for node in pipeline_spec.nodes]
        node_map = {node.name: node for node in pipeline_spec.nodes}
        node_order = {name: index for index, name in enumerate(node_names)}
        dependencies: dict[str, set[str]] = {name: set() for name in node_names}

        for edge in pipeline_spec.edges:
            if edge.source_node not in node_map or edge.target_node not in node_map:
                raise ValidationError("pipeline edge references unknown node")
            dependencies[edge.target_node].add(edge.source_node)

        ordered: list[str] = []
        ready = sorted((name for name, deps in dependencies.items() if not deps), key=node_order.__getitem__)
        while ready:
            current = ready.pop(0)
            ordered.append(current)
            for candidate, deps in dependencies.items():
                if current in deps:
                    deps.remove(current)
                    if not deps and candidate not in ordered and candidate not in ready:
                        ready.append(candidate)
                        ready.sort(key=node_order.__getitem__)

        if len(ordered) != len(node_names):
            raise ValidationError("pipeline contains a cycle")

        return [
            ExecutionStep(
                index=index,
                node_name=name,
                op_name=node_map[name].op_name,
                depends_on=sorted(
                    edge.source_node for edge in pipeline_spec.edges if edge.target_node == name
                ),
            )
            for index, name in enumerate(ordered, start=1)
        ]
