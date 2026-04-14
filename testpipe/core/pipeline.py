"""Pipeline authoring DSL."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from testpipe.spec import PortSpec


@dataclass(slots=True, frozen=True)
class PipelineInputRef:
    port_name: str


@dataclass(slots=True, frozen=True)
class NodeOutputRef:
    node_name: str
    port_name: str


@dataclass(slots=True)
class NodeDefinition:
    name: str
    op: object
    input_bindings: dict[str, PipelineInputRef | NodeOutputRef] = field(default_factory=dict)
    group: str | None = None


class NodeHandle:
    """Reference object returned by ``add_node`` for graph-style binding."""

    def __init__(self, node_name: str) -> None:
        self.node_name = node_name

    def output(self, port_name: str) -> NodeOutputRef:
        return NodeOutputRef(node_name=self.node_name, port_name=port_name)


class Pipeline(ABC):
    """Pipeline DSL used to author execution graphs."""

    version = "1.0"

    def __init__(self) -> None:
        self.pipeline_name = self.__class__.__name__
        self.description = (self.__doc__ or "").strip()
        self.inputs: list[PortSpec] = []
        self.outputs: list[PortSpec] = []
        self.nodes: list[NodeDefinition] = []
        self.current_group: str | None = None
        self.define()

    @abstractmethod
    def define(self) -> None:
        """Define ports and graph nodes."""

    def set_inputs(self, *ports: PortSpec) -> None:
        self.inputs = list(ports)

    def set_outputs(self, *ports: PortSpec) -> None:
        self.outputs = list(ports)

    def input(self, port_name: str) -> PipelineInputRef:
        return PipelineInputRef(port_name=port_name)

    def add_node(
        self,
        name: str,
        op: object,
        *,
        inputs: dict[str, PipelineInputRef | NodeOutputRef] | None = None,
        group: str | None = None,
    ) -> NodeHandle:
        bindings = dict(inputs or {})
        self.nodes.append(
            NodeDefinition(
                name=name,
                op=op,
                input_bindings=bindings,
                group=group or self.current_group,
            )
        )
        return NodeHandle(name)

    def use_group(self, group_name: str | None) -> None:
        self.current_group = group_name

    # Legacy helpers kept for compatibility with generated drafts and older code.
    def set_stage(self, stage_name: str | None) -> None:
        self.use_group(stage_name)

    def add_step(self, name: str, op: object, *, stage: str | None = None) -> NodeHandle:
        return self.add_node(name, op, group=stage)

    def node_output(self, source: str, port_name: str | None = None) -> NodeOutputRef:
        if port_name is None:
            source_node, source_port = source.split(".", 1)
            return NodeOutputRef(node_name=source_node, port_name=source_port)
        return NodeOutputRef(node_name=source, port_name=port_name)

    def connect(self, source: str, target: str) -> None:
        target_node, target_port = target.split(".", 1)
        source_ref = self.node_output(source)
        node = self._require_node(target_node)
        node.input_bindings[target_port] = source_ref

    def _require_node(self, node_name: str) -> NodeDefinition:
        for node in self.nodes:
            if node.name == node_name:
                return node
        raise KeyError(f"unknown node: {node_name}")
