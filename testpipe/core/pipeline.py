"""Pipeline authoring DSL."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from testpipe.spec import PortSpec


@dataclass(slots=True)
class StepDefinition:
    name: str
    op: object
    stage: str | None = None


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
        self.steps: list[StepDefinition] = []
        self.edges: list[EdgeDefinition] = []
        self.current_stage: str | None = None
        self.define()

    @abstractmethod
    def define(self) -> None:
        """Define ports, steps, and edges."""

    def set_inputs(self, *ports: PortSpec) -> None:
        self.inputs = list(ports)

    def set_outputs(self, *ports: PortSpec) -> None:
        self.outputs = list(ports)

    def set_stage(self, stage_name: str | None) -> None:
        self.current_stage = stage_name

    def add_step(self, name: str, op: object, *, stage: str | None = None) -> None:
        self.steps.append(StepDefinition(name=name, op=op, stage=stage or self.current_stage))

    def connect(self, source: str, target: str) -> None:
        source_node, source_port = source.split(".", 1)
        target_node, target_port = target.split(".", 1)
        self.edges.append(
            EdgeDefinition(
                source_node=source_node,
                source_port=source_port,
                target_node=target_node,
                target_port=target_port,
            )
        )
