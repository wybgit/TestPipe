"""Static spec models used by authoring, execution, and export layers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class PortSpec:
    name: str
    type: str
    required: bool = True
    description: str = ""
    artifact_kind: str | None = None
    default: Any | None = None
    expose: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AttrSpec:
    name: str
    type: str
    required: bool = False
    default: Any | None = None
    enum: list[Any] | None = None
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OpSpec:
    version: str
    description: str = ""
    inputs: list[PortSpec] = field(default_factory=list)
    outputs: list[PortSpec] = field(default_factory=list)
    attrs: list[AttrSpec] = field(default_factory=list)

    def attr_map(self) -> dict[str, AttrSpec]:
        return {item.name: item for item in self.attrs}

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "description": self.description,
            "inputs": [item.to_dict() for item in self.inputs],
            "outputs": [item.to_dict() for item in self.outputs],
            "attrs": [item.to_dict() for item in self.attrs],
        }


@dataclass(slots=True)
class InputBindingSpec:
    input_name: str
    source_kind: str
    source_name: str
    source_port: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NodeSpec:
    name: str
    op: str
    op_version: str | None = None
    module: str | None = None
    attrs: dict[str, Any] = field(default_factory=dict)
    input_bindings: list[InputBindingSpec] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EdgeSpec:
    source_node: str
    source_port: str
    target_node: str
    target_port: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PipelineSpec:
    name: str
    version: str
    description: str = ""
    inputs: list[PortSpec] = field(default_factory=list)
    outputs: list[PortSpec] = field(default_factory=list)
    nodes: list[NodeSpec] = field(default_factory=list)
    edges: list[EdgeSpec] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def node_map(self) -> dict[str, NodeSpec]:
        return {node.name: node for node in self.nodes}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "inputs": [item.to_dict() for item in self.inputs],
            "outputs": [item.to_dict() for item in self.outputs],
            "nodes": [item.to_dict() for item in self.nodes],
            "edges": [item.to_dict() for item in self.edges],
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class CaseSpec:
    case_id: str
    name: str
    pipeline: str
    inputs: dict[str, Any]
    expected: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    priority: str = "P2"
    timeout: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TemplateSpec:
    name: str
    task_type: str
    version: str = "1.0"
    description: str = ""
    body: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SkillSpec:
    name: str
    category: str
    template_name: str
    version: str = "1.0"
    description: str = ""
    contract: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class IssueSpec:
    level: str
    field: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CaseCheckReport:
    status: str
    issues: list[IssueSpec] = field(default_factory=list)
    fix_suggestions: list[str] = field(default_factory=list)
    normalized_case: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "issues": [item.to_dict() for item in self.issues],
            "fix_suggestions": self.fix_suggestions,
            "normalized_case": self.normalized_case,
        }


@dataclass(slots=True)
class HostConfig:
    mode: str = "local"
    workdir: str | None = None
    docker_image: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "HostConfig":
        payload = payload or {}
        return cls(
            mode=payload.get("mode", "local"),
            workdir=payload.get("workdir"),
            docker_image=payload.get("docker_image"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DeviceConfig:
    protocol: str = "ssh"
    host: str = ""
    port: int = 22
    user: str = "root"
    workdir: str | None = None
    remote_root: str | None = None
    ssh_options: list[str] = field(default_factory=list)
    connect_timeout: int | None = 10

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "DeviceConfig | None":
        if payload is None:
            return None
        return cls(
            protocol=payload.get("protocol", "ssh"),
            host=payload.get("host", ""),
            port=payload.get("port", 22),
            user=payload.get("user", "root"),
            workdir=payload.get("workdir"),
            remote_root=payload.get("remote_root"),
            ssh_options=list(payload.get("ssh_options", [])),
            connect_timeout=payload.get("connect_timeout", 10),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TransportPolicy:
    mode: str = "local"
    size_threshold_mb: int = 50

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "TransportPolicy | None":
        if payload is None:
            return None
        return cls(
            mode=payload.get("mode", "local"),
            size_threshold_mb=payload.get("size_threshold_mb", 50),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EnvProfile:
    host: HostConfig = field(default_factory=HostConfig)
    device: DeviceConfig | None = None
    transport: TransportPolicy | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def local_default(cls) -> "EnvProfile":
        return cls(host=HostConfig(mode="local"), transport=TransportPolicy(mode="local"))

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "EnvProfile":
        payload = payload or {}
        return cls(
            host=HostConfig.from_dict(payload.get("host")),
            device=DeviceConfig.from_dict(payload.get("device")),
            transport=TransportPolicy.from_dict(payload.get("transport")),
            metadata=payload.get("metadata", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "host": self.host.to_dict(),
            "device": None if self.device is None else self.device.to_dict(),
            "transport": None if self.transport is None else self.transport.to_dict(),
            "metadata": self.metadata,
        }
