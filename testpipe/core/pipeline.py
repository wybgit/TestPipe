"""Pipeline authoring DSL."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from testpipe.spec import PortSpec


@dataclass(slots=True)
class PipelineInputRef:
    input_name: str


@dataclass(slots=True)
class NodeOutputRef:
    node_name: str
    output_name: str


@dataclass(slots=True)
class NodeDefinition:
    name: str
    op: object
    stage: str | None = None
    inputs: dict[str, PipelineInputRef | NodeOutputRef] = field(default_factory=dict)


@dataclass(slots=True)
class OutputDefinition:
    name: str
    source: PipelineInputRef | NodeOutputRef


@dataclass(slots=True)
class NodeHandle:
    name: str

    def output(self, port_name: str) -> NodeOutputRef:
        return NodeOutputRef(node_name=self.name, output_name=port_name)


@dataclass(slots=True)
class EdgeDefinition:
    source_node: str
    source_port: str
    target_node: str
    target_port: str


class Pipeline(ABC):
    """Pipeline DSL used to author execution graphs."""

    version = "1.0"

    def __init__(self) -> None:
        self.pipeline_name = self.__class__.__name__
        self.description = (self.__doc__ or "").strip()
        self.inputs: list[PortSpec] = []
        self.outputs: list[PortSpec] = []
        self.nodes: list[NodeDefinition] = []
        self.edges: list[EdgeDefinition] = []
        self.output_bindings: list[OutputDefinition] = []
        self.current_stage: str | None = None
        self.define()

    @abstractmethod
    def define(self) -> None:
        """Define ports, steps, and edges."""

    def set_inputs(self, *ports: PortSpec) -> None:
        self.inputs = list(ports)

    def set_outputs(self, *ports: PortSpec) -> None:
        self.outputs = list(ports)

    def add_input(
        self,
        name: str,
        type: str,
        *,
        required: bool = True,
        description: str = "",
        artifact_kind: str | None = None,
        default: object | None = None,
    ) -> PipelineInputRef:
        self.inputs.append(
            PortSpec(
                name=name,
                type=type,
                required=required,
                description=description,
                artifact_kind=artifact_kind,
                default=default,
            )
        )
        return PipelineInputRef(input_name=name)

    def input_ref(self, name: str) -> PipelineInputRef:
        if name not in {item.name for item in self.inputs}:
            raise ValueError(f"unknown pipeline input: {name}")
        return PipelineInputRef(input_name=name)

    def add_output(
        self,
        name: str,
        source: PipelineInputRef | NodeOutputRef,
        *,
        type: str,
        required: bool = True,
        description: str = "",
        artifact_kind: str | None = None,
        default: object | None = None,
    ) -> None:
        self.outputs = [item for item in self.outputs if item.name != name]
        self.outputs.append(
            PortSpec(
                name=name,
                type=type,
                required=required,
                description=description,
                artifact_kind=artifact_kind,
                default=default,
            )
        )
        self.output_bindings = [item for item in self.output_bindings if item.name != name]
        self.output_bindings.append(OutputDefinition(name=name, source=source))

    def set_stage(self, stage_name: str | None) -> None:
        self.current_stage = stage_name

    def add_node(
        self,
        name: str,
        op: object,
        *,
        inputs: dict[str, PipelineInputRef | NodeOutputRef] | None = None,
        stage: str | None = None,
        **input_sources: PipelineInputRef | NodeOutputRef,
    ) -> NodeHandle:
        merged_inputs = dict(inputs or {})
        merged_inputs.update(input_sources)
        self.nodes.append(NodeDefinition(name=name, op=op, stage=stage or self.current_stage, inputs=merged_inputs))
        return NodeHandle(name=name)

    def add_step(self, name: str, op: object, *, stage: str | None = None) -> NodeHandle:
        return self.add_node(name, op, stage=stage)

    def connect(self, source: str, target: str) -> None:
        if "." in source:
            source_node, source_port = source.split(".", 1)
            binding: PipelineInputRef | NodeOutputRef = NodeOutputRef(source_node, source_port)
        else:
            binding = PipelineInputRef(source)
        target_node, target_port = target.split(".", 1)
        self._require_node(target_node).inputs[target_port] = binding
        if isinstance(binding, PipelineInputRef):
            return
        self.edges.append(
            EdgeDefinition(
                source_node=binding.node_name,
                source_port=binding.output_name,
                target_node=target_node,
                target_port=target_port,
            )
        )

    def _require_node(self, node_name: str) -> NodeDefinition:
        for node in self.nodes:
            if node.name == node_name:
                return node
        raise ValueError(f"unknown node: {node_name}")
