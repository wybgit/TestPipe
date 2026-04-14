"""Built-in operators for the initial MVP."""

from __future__ import annotations

import json
import shlex
import shutil
import tarfile
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from testpipe.core import TestOp, register_op
from testpipe.spec import AttrSpec, OpSpec, PortSpec


@register_op
class EnvCheckOp(TestOp):
    """Minimal environment check operator."""

    spec = OpSpec(
        op_type="EnvCheck",
        version="1.0",
        category="infra",
        description="Validate the local execution environment",
        inputs=[],
        outputs=[
            PortSpec(
                name="env_ready",
                type="bool",
                description="environment readiness flag",
                expose=False,
            )
        ],
        attrs=[],
    )

    def execute(self, step_context) -> dict[str, bool]:
        return {"env_ready": True}


@register_op
class EchoOp(TestOp):
    """Return the input message once environment is ready."""

    spec = OpSpec(
        op_type="Echo",
        version="1.0",
        category="utility",
        description="Echo a message from pipeline input",
        inputs=[
            PortSpec(name="message", type="string", description="input message"),
            PortSpec(name="env_ready", type="bool", required=False, description="optional env check result"),
        ],
        outputs=[PortSpec(name="echoed_message", type="string", description="echoed message")],
        attrs=[],
    )

    def execute(self, step_context) -> dict[str, str]:
        env_ready = step_context.inputs.get("env_ready", True)
        if not env_ready:
            raise RuntimeError("environment is not ready")
        return {"echoed_message": str(step_context.inputs.require("message"))}


@register_op
class ShellCommandOp(TestOp):
    """Execute a shell command on the host and return stdout."""

    spec = OpSpec(
        op_type="ShellCommand",
        version="1.0",
        category="host",
        description="Execute a shell command through ActionRunner",
        inputs=[],
        outputs=[
            PortSpec(
                name="stdout",
                type="string",
                description="captured stdout",
                expose=False,
            )
        ],
        attrs=[
            AttrSpec(name="command", type="string", required=True, description="shell command to execute"),
            AttrSpec(name="timeout", type="int", required=False, default=30, description="execution timeout"),
        ],
    )

    def execute(self, step_context) -> dict[str, str]:
        result = step_context.host.exec(
            step_context.attrs.require("command"),
            timeout=step_context.attrs.get("timeout", 30),
        )
        return {"stdout": result.stdout.strip()}


@register_op
class WriteTextArtifactOp(TestOp):
    """Materialize plain text content as a run artifact."""

    spec = OpSpec(
        op_type="WriteTextArtifact",
        version="1.0",
        category="artifact",
        description="Write input text to an artifact file",
        inputs=[
            PortSpec(name="content", type="string", required=False, description="text content"),
            PortSpec(name="message", type="string", required=False, description="legacy message alias"),
        ],
        outputs=[PortSpec(name="file_path", type="artifact:path", description="written file path", expose=False)],
        attrs=[
            AttrSpec(name="filename", type="string", required=False, default="payload.txt", description="artifact filename"),
        ],
    )

    def execute(self, step_context) -> dict[str, str]:
        raw_content = step_context.inputs.get("content", step_context.inputs.get("message"))
        if raw_content is None:
            raise KeyError("missing required key: content")
        content = str(raw_content)
        filename = str(step_context.attrs.get("filename", "payload.txt"))
        output_path = Path(step_context.step_dir) / filename
        output_path.write_text(content, encoding="utf-8")
        stable_path = step_context.artifacts.add_file("text_artifact", str(output_path), step_name=step_context.node_name)
        return {"file_path": stable_path}


@register_op
class ReadTextArtifactOp(TestOp):
    """Read plain text from a local artifact file."""

    spec = OpSpec(
        op_type="ReadTextArtifact",
        version="1.0",
        category="artifact",
        description="Read text content from a local artifact path",
        inputs=[PortSpec(name="file_path", type="artifact:path", description="artifact path to read")],
        outputs=[
            PortSpec(name="content", type="string", description="text content"),
            PortSpec(name="downloaded_content", type="string", description="downloaded text content"),
        ],
        attrs=[],
    )

    def execute(self, step_context) -> dict[str, str]:
        source = Path(str(step_context.inputs.require("file_path"))).resolve()
        if not source.exists():
            raise RuntimeError(f"artifact not found: {source}")
        content = source.read_text(encoding="utf-8")
        return {
            "content": content,
            "downloaded_content": content,
        }


@register_op
class ReadJsonArtifactOp(TestOp):
    """Read JSON content from a local artifact file."""

    spec = OpSpec(
        op_type="ReadJsonArtifact",
        version="1.0",
        category="artifact",
        description="Read JSON content from a local artifact path",
        inputs=[PortSpec(name="file_path", type="artifact:path", description="artifact path to read")],
        outputs=[
            PortSpec(name="json_data", type="object", description="decoded JSON object", expose=False),
        ],
        attrs=[],
    )

    def execute(self, step_context) -> dict[str, object]:
        source = Path(str(step_context.inputs.require("file_path"))).resolve()
        if not source.exists():
            raise RuntimeError(f"artifact not found: {source}")
        return {"json_data": json.loads(source.read_text(encoding="utf-8"))}


@register_op
class ResourceFetchOp(TestOp):
    """Materialize a local or git-backed resource into the run workspace."""

    spec = OpSpec(
        op_type="ResourceFetch",
        version="1.0",
        category="resource",
        description="Fetch a local or git-backed resource into the execution workspace",
        inputs=[
            PortSpec(name="resource_path", type="artifact:path", required=False, description="source resource path"),
            PortSpec(name="resource_ref", type="object", required=False, description="structured resource reference"),
            PortSpec(name="repo", type="string", required=False, description="git repository url or local git repo path"),
            PortSpec(name="path", type="string", required=False, description="git repository file or directory path"),
            PortSpec(name="ref", type="string", required=False, description="git ref, branch, tag, or commit"),
            PortSpec(name="model_pattern", type="string", required=False, description="model discovery pattern under a directory"),
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

        simple_git_ref = self._build_simple_git_resource_ref(step_context)
        if resource_ref is not None or simple_git_ref is not None:
            if not isinstance(resource_ref, dict):
                if simple_git_ref is None:
                    raise RuntimeError("resource_ref must be an object")
            resource_ref = simple_git_ref or resource_ref
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

    def _build_simple_git_resource_ref(self, step_context) -> dict[str, object] | None:
        repo = step_context.inputs.get("repo")
        path = step_context.inputs.get("path")
        if repo is None and path is None:
            return None
        if not repo or not path:
            raise RuntimeError("repo and path must be provided together")
        payload: dict[str, object] = {
            "kind": "git_dir",
            "repo": str(repo),
            "subpath": str(path),
        }
        git_ref = step_context.inputs.get("ref")
        if git_ref is not None:
            payload["ref"] = str(git_ref)
        model_pattern = step_context.inputs.get("model_pattern")
        if model_pattern is not None:
            payload["model_pattern"] = str(model_pattern)
        return payload

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
            normalized_subpath = self._normalize_subpath(str(subpath))
            try:
                return self._fetch_git_dir_via_git(
                    step_context,
                    repo=str(repo),
                    subpath=normalized_subpath,
                    git_ref=str(git_ref) if git_ref else None,
                    resource_ref=resource_ref,
                    target_root=target_root,
                )
            except Exception as exc:
                fallback = self._fetch_git_dir_via_github_archive(
                    step_context,
                    repo=str(repo),
                    subpath=normalized_subpath,
                    git_ref=str(git_ref) if git_ref else None,
                    target_root=target_root,
                    cause=exc,
                )
                if fallback is not None:
                    return fallback
                if isinstance(exc, RuntimeError):
                    raise
                raise RuntimeError(str(exc)) from exc

        raise RuntimeError(f"unsupported resource_ref.kind: {kind}")

    def _fetch_git_dir_via_git(
        self,
        step_context,
        *,
        repo: str,
        subpath: str,
        git_ref: str | None,
        resource_ref: dict[str, object],
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
        fetch_command.append("origin")
        if git_ref:
            fetch_command.append(git_ref)
        step_context.host.exec(fetch_command)
        step_context.host.exec(["git", "-C", str(target_root), "checkout", "--detach", "FETCH_HEAD"])

        git_options = resource_ref.get("git", {})
        if isinstance(git_options, dict) and bool(git_options.get("lfs", False)):
            step_context.host.exec(["git", "-C", str(target_root), "lfs", "pull"])

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
        git_ref: str | None,
        target_root: Path,
        cause: Exception,
    ) -> tuple[Path, str] | None:
        archive_url = self._github_archive_url(repo, git_ref)
        if archive_url is None:
            return None

        resolved_commit = self._resolve_remote_commit(step_context, repo, git_ref)
        archive_ref = resolved_commit or git_ref or "HEAD"
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

    def _resolve_remote_commit(self, step_context, repo: str, git_ref: str | None) -> str:
        ref = git_ref or "HEAD"
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


@register_op
class ATCCompileOp(TestOp):
    """Compile a fetched model into an OM artifact, falling back to mock copy for legacy pipelines."""

    spec = OpSpec(
        op_type="ATCCompile",
        version="1.0",
        category="compile",
        description="Compile a model into a local OM artifact",
        inputs=[
            PortSpec(name="model_path", type="artifact:path", description="workspace model path"),
            PortSpec(name="soc_version", type="string", required=False, description="target soc version"),
            PortSpec(name="atc_options", type="object", required=False, description="extra atc options"),
            PortSpec(name="env_script", type="string", required=False, description="cann env script"),
            PortSpec(name="output_name", type="string", required=False, description="output om filename or prefix"),
        ],
        outputs=[PortSpec(name="om_path", type="artifact:path", description="compiled om path")],
        attrs=[
            AttrSpec(name="output_name", type="string", required=False, default="compiled_model.om", description="compiled output filename"),
            AttrSpec(name="timeout", type="int", required=False, default=30, description="command timeout"),
            AttrSpec(name="framework", type="int", required=False, default=5, description="atc framework id"),
            AttrSpec(
                name="env_script",
                type="string",
                required=False,
                default="/home/wyb/Ascend/cann-8.5.0/set_env.sh",
                description="cann environment script path",
            ),
        ],
    )

    def execute(self, step_context) -> dict[str, str]:
        source = Path(str(step_context.inputs.require("model_path"))).resolve()
        if not source.exists():
            raise RuntimeError(f"model not found: {source}")

        output_name = str(step_context.inputs.get("output_name", step_context.attrs.get("output_name", "compiled_model.om")))
        timeout = step_context.attrs.get("timeout", 30)
        soc_version = step_context.inputs.get("soc_version")
        if soc_version in {None, ""}:
            destination = Path(step_context.step_dir) / output_name
            step_context.host.exec(["cp", str(source), str(destination)], timeout=timeout)
        else:
            env_script = str(step_context.inputs.get("env_script", step_context.attrs.get("env_script", "/home/wyb/Ascend/cann-8.5.0/set_env.sh")))
            if not Path(env_script).expanduser().exists():
                raise RuntimeError(f"cann env script not found: {env_script}")
            output_prefix = self._output_prefix(Path(step_context.step_dir), output_name)
            compile_command = self._build_atc_command(
                model_path=source,
                output_prefix=output_prefix,
                framework=int(step_context.attrs.get("framework", 5)),
                soc_version=str(soc_version),
                atc_options=step_context.inputs.get("atc_options"),
            )
            command = f"source {shlex.quote(env_script)} && {' '.join(shlex.quote(part) for part in compile_command)}"
            step_context.host.exec(["bash", "-lc", command], timeout=timeout)
            destination = Path(f"{output_prefix}.om")
            if not destination.exists():
                raise RuntimeError(f"atc did not produce expected om file: {destination}")

        stable_path = step_context.artifacts.add_file(
            "compiled_model",
            str(destination),
            step_name=step_context.node_name,
        )
        return {"om_path": stable_path}

    def _output_prefix(self, step_dir: Path, output_name: str) -> Path:
        output_path = step_dir / output_name
        if output_path.suffix == ".om":
            return output_path.with_suffix("")
        return output_path

    def _build_atc_command(
        self,
        *,
        model_path: Path,
        output_prefix: Path,
        framework: int,
        soc_version: str,
        atc_options: object,
    ) -> list[str]:
        command = [
            "atc",
            f"--model={model_path}",
            f"--framework={framework}",
            f"--output={output_prefix}",
            f"--soc_version={soc_version}",
        ]
        command.extend(self._render_extra_atc_args(atc_options))
        return command

    def _render_extra_atc_args(self, atc_options: object) -> list[str]:
        if atc_options is None:
            return []
        if not isinstance(atc_options, dict):
            raise RuntimeError("atc_options must be an object")
        reserved = {"model", "framework", "output", "soc_version"}
        rendered: list[str] = []
        for key in sorted(atc_options.keys()):
            if key in reserved:
                raise RuntimeError(f"atc_options cannot override reserved argument: {key}")
            value = atc_options[key]
            if isinstance(value, bool):
                value = "true" if value else "false"
            rendered.append(f"--{key}={value}")
        return rendered


@register_op
class TransferOp(TestOp):
    """Transfer an artifact into a mock device staging directory."""

    spec = OpSpec(
        op_type="Transfer",
        version="1.0",
        category="transfer",
        description="Transfer a local artifact into a staged target directory",
        inputs=[PortSpec(name="local_path", type="artifact:path", description="local artifact path")],
        outputs=[PortSpec(name="remote_path", type="artifact:path", description="staged remote path")],
        attrs=[
            AttrSpec(name="target_dir", type="string", required=False, default="device", description="staging directory name"),
            AttrSpec(name="timeout", type="int", required=False, default=30, description="command timeout"),
        ],
    )

    def execute(self, step_context) -> dict[str, str]:
        source = Path(str(step_context.inputs.require("local_path"))).resolve()
        if not source.exists():
            raise RuntimeError(f"local artifact not found: {source}")

        target_dir = Path(step_context.artifacts.root_dir) / str(step_context.attrs.get("target_dir", "device"))
        target_dir.mkdir(parents=True, exist_ok=True)
        destination = target_dir / source.name
        step_context.host.exec(["cp", str(source), str(destination)], timeout=step_context.attrs.get("timeout", 30))
        return {"remote_path": str(destination)}


@register_op
class TransferPutOp(TestOp):
    """Upload an artifact to the configured device through TransferExecutor."""

    spec = OpSpec(
        op_type="TransferPut",
        version="1.0",
        category="transfer",
        description="Transfer a local artifact to the configured device path",
        inputs=[PortSpec(name="local_path", type="artifact:path", description="local artifact path")],
        outputs=[PortSpec(name="remote_path", type="artifact:path", description="device-side artifact path")],
        attrs=[
            AttrSpec(name="remote_path", type="string", required=True, description="destination path on device"),
        ],
    )

    def execute(self, step_context) -> dict[str, str]:
        if step_context.transfer is None:
            raise RuntimeError("transfer executor is not configured")
        remote_path = step_context.transfer.put(
            str(step_context.inputs.require("local_path")),
            str(step_context.attrs.require("remote_path")),
        )
        return {"remote_path": remote_path}


@register_op
class TransferGetOp(TestOp):
    """Download an artifact from the configured device through TransferExecutor."""

    spec = OpSpec(
        op_type="TransferGet",
        version="1.0",
        category="transfer",
        description="Transfer a remote device artifact back to the local workspace",
        inputs=[],
        outputs=[PortSpec(name="local_path", type="artifact:path", description="downloaded local artifact path", expose=False)],
        attrs=[
            AttrSpec(name="remote_path", type="string", required=True, description="source path on device"),
            AttrSpec(name="local_name", type="string", required=False, default="downloaded.txt", description="local output filename"),
        ],
    )

    def execute(self, step_context) -> dict[str, str]:
        if step_context.transfer is None:
            raise RuntimeError("transfer executor is not configured")
        local_name = str(step_context.attrs.get("local_name", "downloaded.txt"))
        local_path = Path(step_context.step_dir) / local_name
        downloaded_path = step_context.transfer.get(
            str(step_context.attrs.require("remote_path")),
            str(local_path),
        )
        stable_path = step_context.artifacts.add_file("downloaded_artifact", downloaded_path, step_name=step_context.node_name)
        return {"local_path": stable_path}


@register_op
class DeviceCommandOp(TestOp):
    """Execute a command on the configured device."""

    spec = OpSpec(
        op_type="DeviceCommand",
        version="1.0",
        category="device",
        description="Execute a shell command on the configured device executor",
        inputs=[],
        outputs=[PortSpec(name="device_stdout", type="string", description="captured device stdout")],
        attrs=[
            AttrSpec(name="command", type="string", required=True, description="shell command to execute on device"),
            AttrSpec(name="timeout", type="int", required=False, default=30, description="execution timeout"),
        ],
    )

    def execute(self, step_context) -> dict[str, str]:
        if step_context.device is None:
            raise RuntimeError("device executor is not configured")
        result = step_context.device.exec(
            str(step_context.attrs.require("command")),
            timeout=step_context.attrs.get("timeout", 30),
        )
        return {"device_stdout": result.stdout.strip()}


@register_op
class TextEqualsOp(TestOp):
    """Compare two text inputs and emit a business-friendly pass/fail result."""

    spec = OpSpec(
        op_type="TextEquals",
        version="1.0",
        category="assert",
        description="Compare actual and expected text content",
        inputs=[
            PortSpec(name="actual_text", type="string", description="actual text content"),
            PortSpec(name="expected_text", type="string", description="expected text content"),
        ],
        outputs=[
            PortSpec(name="test_passed", type="bool", description="comparison result"),
            PortSpec(
                name="mismatch_reason",
                type="string",
                description="comparison mismatch description",
                expose=False,
            ),
        ],
        attrs=[
            AttrSpec(name="strip", type="bool", required=False, default=True, description="strip leading and trailing whitespace"),
            AttrSpec(
                name="normalize_line_endings",
                type="bool",
                required=False,
                default=True,
                description="normalize CRLF/LF differences before comparing",
            ),
        ],
    )

    def execute(self, step_context) -> dict[str, bool | str]:
        actual = self._normalize_text(
            str(step_context.inputs.require("actual_text")),
            strip=bool(step_context.attrs.get("strip", True)),
            normalize_line_endings=bool(step_context.attrs.get("normalize_line_endings", True)),
        )
        expected = self._normalize_text(
            str(step_context.inputs.require("expected_text")),
            strip=bool(step_context.attrs.get("strip", True)),
            normalize_line_endings=bool(step_context.attrs.get("normalize_line_endings", True)),
        )

        if actual == expected:
            return {"test_passed": True, "mismatch_reason": ""}
        return {
            "test_passed": False,
            "mismatch_reason": f"expected {expected!r}, got {actual!r}",
        }

    def _normalize_text(self, value: str, *, strip: bool, normalize_line_endings: bool) -> str:
        if normalize_line_endings:
            value = value.replace("\r\n", "\n").replace("\r", "\n")
        if strip:
            value = value.strip()
        return value


@register_op
class PathExistsOp(TestOp):
    """Check whether a local path exists."""

    spec = OpSpec(
        op_type="PathExists",
        version="1.0",
        category="assert",
        description="Check whether a local file or directory exists",
        inputs=[PortSpec(name="target_path", type="artifact:path", description="path to inspect")],
        outputs=[
            PortSpec(name="path_exists", type="bool", description="path existence result"),
            PortSpec(name="checked_path", type="artifact:path", description="normalized checked path", expose=False),
        ],
        attrs=[],
    )

    def execute(self, step_context) -> dict[str, bool | str]:
        target_path = Path(str(step_context.inputs.require("target_path"))).expanduser().resolve()
        return {
            "path_exists": target_path.exists(),
            "checked_path": str(target_path),
        }


@register_op
class ValueCompareOp(TestOp):
    """Compare an input value against a configured expected value."""

    spec = OpSpec(
        op_type="ValueCompare",
        version="1.0",
        category="assert",
        description="Compare an actual value against an expected value using a configured operator",
        inputs=[
            PortSpec(name="actual_value", type="any", description="actual value to compare"),
            PortSpec(name="expected_value", type="any", required=False, description="expected comparison value"),
            PortSpec(name="operator", type="string", required=False, description="comparison operator"),
        ],
        outputs=[
            PortSpec(name="test_passed", type="bool", description="comparison result"),
            PortSpec(name="comparison_detail", type="string", description="comparison detail", expose=False),
        ],
        attrs=[
            AttrSpec(
                name="operator",
                type="string",
                required=False,
                default="eq",
                enum=["eq", "ne", "gt", "ge", "lt", "le"],
                description="comparison operator",
            ),
            AttrSpec(name="expected_value", type="any", required=True, description="expected comparison value"),
        ],
    )

    def execute(self, step_context) -> dict[str, bool | str]:
        actual = step_context.inputs.require("actual_value")
        expected = step_context.inputs.get("expected_value", step_context.attrs.require("expected_value"))
        operator = str(step_context.inputs.get("operator", step_context.attrs.get("operator", "eq")))

        if operator in {"eq", "ne"}:
            passed = actual == expected if operator == "eq" else actual != expected
        else:
            lhs = self._to_float(actual)
            rhs = self._to_float(expected)
            passed = {
                "gt": lhs > rhs,
                "ge": lhs >= rhs,
                "lt": lhs < rhs,
                "le": lhs <= rhs,
            }[operator]

        detail = f"operator={operator}, expected={expected!r}, actual={actual!r}"
        return {
            "test_passed": passed,
            "comparison_detail": detail,
        }

    def _to_float(self, value: object) -> float:
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"value is not numeric: {value!r}") from exc


@register_op
class JsonObjectAssertOp(TestOp):
    """Assert selected fields inside a JSON object."""

    spec = OpSpec(
        op_type="JsonObjectAssert",
        version="1.0",
        category="assert",
        description="Validate selected JSON fields against expected values",
        inputs=[
            PortSpec(name="json_data", type="object", description="decoded JSON object"),
            PortSpec(name="expected_json", type="object", required=False, description="expected JSON fields"),
        ],
        outputs=[
            PortSpec(name="test_passed", type="bool", description="assertion result"),
            PortSpec(name="mismatch_reason", type="string", description="assertion mismatch details", expose=False),
        ],
        attrs=[
            AttrSpec(name="expectations", type="object", required=False, default=None, description="fallback expected JSON fields"),
        ],
    )

    def execute(self, step_context) -> dict[str, bool | str]:
        actual = step_context.inputs.require("json_data")
        expectations = step_context.inputs.get("expected_json", step_context.attrs.get("expectations"))
        if expectations is None:
            raise ValueError("expected_json input or expectations attr is required")
        if not isinstance(actual, dict):
            raise ValueError("json_data must be a JSON object")
        if not isinstance(expectations, dict):
            raise ValueError("expected_json/expectations must be a JSON object")

        mismatches: list[str] = []
        for field_path, expected_value in expectations.items():
            actual_value = self._resolve_field(actual, str(field_path))
            if actual_value != expected_value:
                mismatches.append(f"{field_path} expected {expected_value!r}, got {actual_value!r}")

        return {
            "test_passed": not mismatches,
            "mismatch_reason": "; ".join(mismatches),
        }

    def _resolve_field(self, payload: dict[str, object], field_path: str) -> object:
        current: object = payload
        for token in field_path.split("."):
            if isinstance(current, dict):
                if token not in current:
                    return None
                current = current[token]
                continue
            if isinstance(current, list):
                try:
                    index = int(token)
                except ValueError:
                    return None
                if index < 0 or index >= len(current):
                    return None
                current = current[index]
                continue
            return None
        return current
