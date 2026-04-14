"""Resource acquisition operators."""

from __future__ import annotations

import shutil
from pathlib import Path

from testpipe.core import TestOp, register_op
from testpipe.spec import OpSpec, PortSpec


@register_op
class ResourceFetchOp(TestOp):
    """Materialize a local or git-backed resource into the run workspace."""

    spec = OpSpec(
        version="1.0",
        description="Fetch a local or git-backed resource into the execution workspace",
        inputs=[
            PortSpec(name="resource_path", type="artifact:path", required=False, description="source resource path"),
            PortSpec(name="resource_ref", type="object", required=False, description="structured resource reference"),
        ],
        outputs=[
            PortSpec(
                name="resource_root",
                type="artifact:path",
                description="materialized resource root",
            ),
            PortSpec(
                name="model_path",
                type="artifact:path",
                description="workspace-local model path",
            ),
            PortSpec(
                name="resolved_commit",
                type="string",
                required=False,
                description="resolved git commit when resource is fetched from git",
            ),
        ],
        attrs=[],
    )

    def execute(self, step_context) -> dict[str, str]:
        resource_ref = step_context.inputs.get("resource_ref")
        resolved_commit = ""
        target_root = Path(step_context.artifacts.root_dir) / f"{step_context.node_name}_resource"
        self._remove_path(target_root)

        if resource_ref is not None:
            if not isinstance(resource_ref, dict):
                raise RuntimeError("resource_ref must be an object")
            materialized_path, resolved_commit = self._fetch_resource_ref(step_context, resource_ref, target_root)
        else:
            source_root = self._resolve_local_resource(step_context)
            materialized_path = self._materialize_local_resource(source_root, target_root)

        model_path = self._discover_model_path(
            materialized_path,
            pattern=self._resource_model_pattern(resource_ref),
        )
        return {
            "resource_root": str(materialized_path),
            "model_path": str(model_path),
            "resolved_commit": resolved_commit,
        }

    def _fetch_resource_ref(self, step_context, resource_ref: dict[str, object], target_root: Path) -> tuple[Path, str]:
        kind = str(resource_ref.get("kind", "")).strip()
        if kind in {"local_dir", "local_file"}:
            path = resource_ref.get("path")
            if not path:
                raise RuntimeError("resource_ref.path is required for local resources")
            source = Path(str(path)).expanduser().resolve()
            if not source.exists():
                raise RuntimeError(f"resource not found: {source}")
            return self._materialize_local_resource(source, target_root), ""

        if kind == "git_dir":
            repo = resource_ref.get("repo")
            subpath = resource_ref.get("subpath")
            git_ref = resource_ref.get("ref")
            if not repo or not subpath:
                raise RuntimeError("resource_ref.repo and resource_ref.subpath are required for git_dir")
            target_root.mkdir(parents=True, exist_ok=True)
            normalized_subpath = self._normalize_subpath(str(subpath))

            step_context.host.exec(["git", "init", str(target_root)])
            step_context.host.exec(["git", "-C", str(target_root), "remote", "add", "origin", str(repo)])
            if self._supports_partial_clone(str(repo)):
                step_context.host.exec(["git", "-C", str(target_root), "config", "extensions.partialClone", "origin"])
                step_context.host.exec(["git", "-C", str(target_root), "config", "remote.origin.promisor", "true"])
                step_context.host.exec(["git", "-C", str(target_root), "config", "remote.origin.partialclonefilter", "blob:none"])
            step_context.host.exec(["git", "-C", str(target_root), "sparse-checkout", "init", "--no-cone"])
            step_context.host.exec(["git", "-C", str(target_root), "sparse-checkout", "set", "--no-cone", normalized_subpath])

            fetch_command = ["git", "-C", str(target_root), "fetch", "--depth=1"]
            if self._supports_partial_clone(str(repo)):
                fetch_command.append("--filter=blob:none")
            fetch_command.append("origin")
            if git_ref:
                fetch_command.append(str(git_ref))
            step_context.host.exec(fetch_command)
            step_context.host.exec(["git", "-C", str(target_root), "checkout", "--detach", "FETCH_HEAD"])

            git_options = resource_ref.get("git", {})
            if isinstance(git_options, dict) and bool(git_options.get("lfs", False)):
                step_context.host.exec(["git", "-C", str(target_root), "lfs", "pull"])

            resolved_commit = step_context.host.exec(["git", "-C", str(target_root), "rev-parse", "HEAD"]).stdout.strip()
            materialized_path = (target_root / normalized_subpath).resolve()
            if not materialized_path.exists():
                raise RuntimeError(f"git resource subpath not found: {materialized_path}")
            self._remove_path(target_root / ".git")
            return materialized_path, resolved_commit

        raise RuntimeError(f"unsupported resource_ref.kind: {kind}")

    def _materialize_local_resource(self, source: Path, target_root: Path) -> Path:
        if source.is_dir():
            target_root.mkdir(parents=True, exist_ok=True)
            destination = target_root / source.name
            shutil.copytree(source, destination)
            return destination
        target_root.mkdir(parents=True, exist_ok=True)
        destination = target_root / source.name
        shutil.copy2(source, destination)
        return destination

    def _normalize_subpath(self, subpath: str) -> str:
        normalized = subpath.strip().strip("/")
        if not normalized:
            raise RuntimeError("resource_ref.subpath must not be empty")
        return normalized

    def _supports_partial_clone(self, repo: str) -> bool:
        lowered = repo.lower()
        return lowered.startswith(("http://", "https://", "ssh://", "git@"))

    def _remove_path(self, path: Path) -> None:
        if not path.exists():
            return
        if path.is_dir():
            shutil.rmtree(path)
            return
        path.unlink()

    def _resolve_local_resource(self, step_context) -> Path:
        source = Path(str(step_context.inputs.require("resource_path"))).expanduser().resolve()
        if not source.exists():
            raise RuntimeError(f"resource not found: {source}")
        return source

    def _resource_model_pattern(self, resource_ref: object) -> str:
        if isinstance(resource_ref, dict):
            return str(resource_ref.get("model_pattern", "*.onnx"))
        return "*.onnx"

    def _discover_model_path(self, resource_root: Path, *, pattern: str) -> Path:
        if resource_root.is_file():
            return resource_root

        matches = sorted(path for path in resource_root.rglob(pattern) if path.is_file())
        if len(matches) != 1:
            raise RuntimeError(f"expected exactly one model matching {pattern!r}, found {len(matches)}")
        return matches[0]
