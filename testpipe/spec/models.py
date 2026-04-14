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
class NodeSpec:
    name: str
    op_name: str
    op_version: str | None = None
    stage: str | None = None
    attrs: dict[str, Any] = field(default_factory=dict)
    input_bindings: list["InputBindingSpec"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "op_name": self.op_name,
            "op_version": self.op_version,
            "stage": self.stage,
            "attrs": self.attrs,
            "input_bindings": [item.to_dict() for item in self.input_bindings],
        }


@dataclass(slots=True)
class InputBindingSpec:
    target_port: str
    source_type: str
    source_name: str
    source_port: str | None = None

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
    output_bindings: list["OutputBindingSpec"] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def node_map(self) -> dict[str, NodeSpec]:
        return {node.name: node for node in self.nodes}

    def output_binding_map(self) -> dict[str, "OutputBindingSpec"]:
        return {binding.output_name: binding for binding in self.output_bindings}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "inputs": [item.to_dict() for item in self.inputs],
            "outputs": [item.to_dict() for item in self.outputs],
            "nodes": [item.to_dict() for item in self.nodes],
            "edges": [item.to_dict() for item in self.edges],
            "output_bindings": [item.to_dict() for item in self.output_bindings],
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class OutputBindingSpec:
    output_name: str
    source_type: str
    source_name: str
    source_port: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CaseSpec:
    case_id: str
    pipeline: str
    inputs: dict[str, Any]
    inputs_by_node: dict[str, dict[str, Any]] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    expected: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    priority: str = "P2"
    timeout: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    name: str = ""

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
    conda_env: str | None = None
    docker_image: str | None = None
    docker_run_args: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "HostConfig":
        payload = payload or {}
        return cls(
            mode=payload.get("mode", "local"),
            workdir=payload.get("workdir"),
            conda_env=payload.get("conda_env"),
            docker_image=payload.get("docker_image"),
            docker_run_args=list(payload.get("docker_run_args", [])),
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


@dataclass(slots=True)
class FrameworkEnvBinding:
    enabled: bool = True
    profile: EnvProfile = field(default_factory=EnvProfile.local_default)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "FrameworkEnvBinding":
        payload = payload or {}
        raw_profile = payload.get("env_profile", payload.get("profile"))
        if raw_profile is None:
            raw_profile = {
                key: value
                for key, value in payload.items()
                if key not in {"enabled", "env_profile", "profile"}
            }
        if not isinstance(raw_profile, dict):
            raise ValueError("framework env binding profile must be a mapping")
        return cls(
            enabled=bool(payload.get("enabled", True)),
            profile=EnvProfile.from_dict(raw_profile),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "env_profile": self.profile.to_dict(),
        }


@dataclass(slots=True)
class FrameworkConfig:
    default_env: str = "local"
    envs: dict[str, FrameworkEnvBinding] = field(default_factory=dict)

    @classmethod
    def default(cls) -> "FrameworkConfig":
        return cls(
            default_env="local",
            envs={
                "local": FrameworkEnvBinding(
                    enabled=True,
                    profile=EnvProfile.local_default(),
                )
            },
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "FrameworkConfig":
        if not payload:
            return cls.default()
        raw = payload.get("testpipe", payload)
        if not isinstance(raw, dict):
            raise ValueError("framework config document must be a mapping")
        envs_raw = raw.get("envs", raw.get("profiles", {}))
        if not isinstance(envs_raw, dict):
            raise ValueError("framework config envs/profiles must be a mapping")
        envs = {
            str(name): FrameworkEnvBinding.from_dict(item if isinstance(item, dict) else {})
            for name, item in envs_raw.items()
        }
        config = cls(
            default_env=str(raw.get("default_env", raw.get("default_profile", "local"))),
            envs=envs or cls.default().envs,
        )
        if config.default_env not in config.envs:
            if config.default_env == "local":
                config.envs.setdefault("local", FrameworkEnvBinding(enabled=True, profile=EnvProfile.local_default()))
            else:
                raise ValueError(f"default env not found in framework config: {config.default_env}")
        return config

    def resolve_env_profile(self, ref: str | None = None) -> EnvProfile:
        name = ref or self.default_env
        if name in {"", "local_default"} and name not in self.envs:
            return EnvProfile.local_default()
        binding = self.envs.get(name)
        if binding is None:
            raise ValueError(f"env profile not found in framework config: {name}")
        if not binding.enabled:
            raise ValueError(f"env profile is disabled in framework config: {name}")
        return binding.profile

    def to_dict(self) -> dict[str, Any]:
        return {
            "default_env": self.default_env,
            "envs": {name: item.to_dict() for name, item in self.envs.items()},
        }
