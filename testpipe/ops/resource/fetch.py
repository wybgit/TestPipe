"""Resource materialization operators."""

from __future__ import annotations

import shutil
import tarfile
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from testpipe.core import TestOp, register_op
from testpipe.spec import AttrSpec, OpSpec, PortSpec


@register_op
class ResourceFetchOp(TestOp):
    """Materialize a git-backed resource into the run workspace."""

    spec = OpSpec(
        version="1.0",
        description="Fetch a git repository subpath into the execution workspace and resolve a model file",
        inputs=[
            PortSpec(name="repo", type="string", description="git repository url or local git repo path"),
            PortSpec(name="branch", type="string", description="git branch to fetch"),
            PortSpec(name="path", type="string", description="git repository file or directory path"),
        ],
        outputs=[
            PortSpec(
                name="model_path",
                type="artifact:path",
                description="model file path matched by model_pattern",
            ),
        ],
        attrs=[
            AttrSpec(
                name="model_pattern",
                type="string",
                required=False,
                default="*.onnx",
                description="model discovery pattern under the fetched directory",
            ),
        ],
    )

    def execute(self, step_context) -> dict[str, str]:
        target_root = Path(step_context.artifacts.root_dir) / f"{step_context.node_name}_resource"
        self._remove_path(target_root)
        materialized_path, _ = self._fetch_git_dir(
            step_context,
            repo=str(step_context.inputs.require("repo")),
            subpath=self._normalize_subpath(str(step_context.inputs.require("path"))),
            branch=str(step_context.inputs.require("branch")),
            target_root=target_root,
        )

        model_path = self._discover_model_path(
            materialized_path,
            pattern=str(step_context.attrs.get("model_pattern", "*.onnx")),
        )
        return {
            "model_path": str(model_path),
        }

    def _fetch_git_dir(
        self,
        step_context,
        *,
        repo: str,
        subpath: str,
        branch: str,
        target_root: Path,
    ) -> tuple[Path, str]:
        try:
            return self._fetch_git_dir_via_git(
                step_context,
                repo=repo,
                subpath=subpath,
                branch=branch,
                target_root=target_root,
            )
        except Exception as exc:
            fallback = self._fetch_git_dir_via_github_archive(
                step_context,
                repo=repo,
                subpath=subpath,
                branch=branch,
                target_root=target_root,
                cause=exc,
            )
            if fallback is not None:
                return fallback
            if isinstance(exc, RuntimeError):
                raise
            raise RuntimeError(str(exc)) from exc

    def _fetch_git_dir_via_git(
        self,
        step_context,
        *,
        repo: str,
        subpath: str,
        branch: str,
        target_root: Path,
    ) -> tuple[Path, str]:
        self._remove_path(target_root)
        target_root.mkdir(parents=True, exist_ok=True)

        step_context.host.exec(["git", "init", str(target_root)])
        step_context.host.exec(["git", "-C", str(target_root), "remote", "add", "origin", repo])
        if self._supports_partial_clone(repo):
            step_context.host.exec(["git", "-C", str(target_root), "config", "extensions.partialClone", "origin"])
            step_context.host.exec(["git", "-C", str(target_root), "config", "remote.origin.promisor", "true"])
            step_context.host.exec(["git", "-C", str(target_root), "config", "remote.origin.partialclonefilter", "blob:none"])
        step_context.host.exec(["git", "-C", str(target_root), "sparse-checkout", "init", "--no-cone"])
        step_context.host.exec(["git", "-C", str(target_root), "sparse-checkout", "set", "--no-cone", subpath])

        fetch_command = ["git", "-C", str(target_root), "fetch", "--depth=1"]
        if self._supports_partial_clone(repo):
            fetch_command.append("--filter=blob:none")
        fetch_command.extend(["origin", branch])
        step_context.host.exec(fetch_command)
        step_context.host.exec(["git", "-C", str(target_root), "checkout", "--detach", "FETCH_HEAD"])

        resolved_commit = step_context.host.exec(["git", "-C", str(target_root), "rev-parse", "HEAD"]).stdout.strip()
        materialized_path = (target_root / subpath).resolve()
        if not materialized_path.exists():
            raise RuntimeError(f"git resource subpath not found: {materialized_path}")
        self._remove_path(target_root / ".git")
        return materialized_path, resolved_commit

    def _fetch_git_dir_via_github_archive(
        self,
        step_context,
        *,
        repo: str,
        subpath: str,
        branch: str,
        target_root: Path,
        cause: Exception,
    ) -> tuple[Path, str] | None:
        archive_url = self._github_archive_url(repo, branch)
        if archive_url is None:
            return None

        resolved_commit = self._resolve_remote_commit(step_context, repo, branch)
        archive_ref = resolved_commit or branch or "HEAD"
        archive_url = self._github_archive_url(repo, archive_ref)
        if archive_url is None:
            return None

        self._remove_path(target_root)
        target_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="testpipe_github_archive_") as tmp_dir:
            tmp_root = Path(tmp_dir)
            archive_path = tmp_root / "repo.tar.gz"
            extract_root = tmp_root / "extract"
            self._download_url(archive_url, archive_path)
            extract_root.mkdir(parents=True, exist_ok=True)
            with tarfile.open(archive_path, mode="r:gz") as handle:
                handle.extractall(extract_root)
            extracted_items = list(extract_root.iterdir())
            if len(extracted_items) != 1:
                raise RuntimeError(f"unexpected github archive layout for repo: {repo}")
            archive_root = extracted_items[0]
            materialized_source = (archive_root / subpath).resolve()
            if not materialized_source.exists():
                raise RuntimeError(f"github archive subpath not found: {materialized_source}")
            materialized_path = self._materialize_local_resource(materialized_source, target_root)

        self._record_internal_action(
            step_context,
            action_type="resource.archive_download",
            command=f"github-archive-download {archive_url}",
            stdout=str(materialized_path),
            stderr=f"git fetch fallback: {cause}",
        )
        return materialized_path, resolved_commit

    def _resolve_remote_commit(self, step_context, repo: str, branch: str | None) -> str:
        ref = branch or "HEAD"
        try:
            result = step_context.host.exec(["git", "ls-remote", repo, ref])
        except Exception:
            return ""
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if not lines:
            return ""
        return lines[0].split()[0]

    def _github_archive_url(self, repo: str, ref: str | None) -> str | None:
        parsed = urlparse(repo)
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != "github.com":
            return None
        path = parsed.path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]
        tokens = [token for token in path.split("/") if token]
        if len(tokens) != 2:
            return None
        owner, repo_name = tokens
        archive_ref = ref or "HEAD"
        return f"https://codeload.github.com/{owner}/{repo_name}/tar.gz/{archive_ref}"

    def _download_url(self, url: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with urlopen(url) as response, destination.open("wb") as handle:  # noqa: S310
            shutil.copyfileobj(response, handle)

    def _record_internal_action(
        self,
        step_context,
        *,
        action_type: str,
        command: str,
        stdout: str,
        stderr: str,
    ) -> None:
        step_context.host.action_runner.trace_recorder.record(
            step_name=step_context.node_name,
            action_type=action_type,
            request={
                "command": command,
                "target": "local",
            },
            response={
                "action_type": action_type,
                "target": "local",
                "command": command,
                "returncode": 0,
                "stdout": stdout,
                "stderr": stderr,
            },
        )

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
            raise RuntimeError("path must not be empty")
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

    def _discover_model_path(self, resource_root: Path, *, pattern: str) -> Path:
        if resource_root.is_file():
            return resource_root

        matches = sorted(path for path in resource_root.rglob(pattern) if path.is_file())
        if len(matches) != 1:
            raise RuntimeError(f"expected exactly one model matching {pattern!r}, found {len(matches)}")
        return matches[0]
