"""Execution backends."""

from __future__ import annotations

from pathlib import Path
import shlex

from testpipe.core.exceptions import StepExecutionError


class HostExecutor:
    """Local host executor for the initial MVP."""

    def __init__(self, action_runner, step_context, env_profile=None) -> None:
        self.action_runner = action_runner
        self.step_context = step_context
        self.env_profile = env_profile

    def exec(
        self,
        command: str | list[str],
        *,
        timeout: int | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ):
        prepared_command, prepared_cwd, prepared_env = self._prepare_command(command, cwd=cwd, env=env)
        result = self.action_runner.run_local(
            prepared_command,
            step_name=self.step_context.node_name,
            stdout_log=Path(self.step_context.stdout_log_path),
            stderr_log=Path(self.step_context.stderr_log_path),
            cwd=prepared_cwd,
            env=prepared_env,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise StepExecutionError(self.step_context.node_name, self._failure_message(result, prepared_command))
        return result

    def _prepare_command(
        self,
        command: str | list[str],
        *,
        cwd: str | None,
        env: dict[str, str] | None,
    ) -> tuple[str | list[str], str | None, dict[str, str] | None]:
        if self.env_profile is None:
            return command, cwd, env

        host = self.env_profile.host
        mode = host.mode or "local"
        if mode == "local":
            return command, cwd, env

        rendered_command = command if isinstance(command, str) else shlex.join([str(item) for item in command])

        if mode == "conda":
            if not host.conda_env:
                raise StepExecutionError(self.step_context.node_name, "host.conda_env is required for conda mode")
            return ["conda", "run", "-n", host.conda_env, "bash", "-lc", rendered_command], cwd, env

        if mode == "docker":
            if not host.docker_image:
                raise StepExecutionError(self.step_context.node_name, "host.docker_image is required for docker mode")
            mount_paths = self._docker_mount_paths(cwd)
            docker_command = ["docker", "run", "--rm"]
            for path in mount_paths:
                docker_command.extend(["-v", f"{path}:{path}"])
            for item in host.docker_run_args:
                docker_command.append(item)
            if env:
                for key, value in env.items():
                    docker_command.extend(["-e", f"{key}={value}"])
            docker_command.extend(
                [
                    "-w",
                    cwd or host.workdir or str(Path.cwd().resolve()),
                    host.docker_image,
                    "bash",
                    "-lc",
                    rendered_command,
                ]
            )
            return docker_command, None, None

        raise StepExecutionError(self.step_context.node_name, f"unsupported host mode: {mode}")

    def _docker_mount_paths(self, cwd: str | None) -> list[str]:
        candidates = {str(Path.cwd().resolve()), "/tmp"}
        if cwd:
            candidates.add(str(Path(cwd).resolve()))
        if self.env_profile is not None and self.env_profile.host.workdir:
            candidates.add(str(Path(self.env_profile.host.workdir).resolve()))
        return sorted(path for path in candidates if Path(path).exists())

    def _failure_message(self, result, command: str | list[str]) -> str:
        detail = (result.stderr or "").strip() or (result.stdout or "").strip()
        return detail or f"command failed: {command}"


class DeviceExecutor:
    """Device executor backed by local mock mode or SSH commands."""

    def __init__(self, action_runner, env_profile, step_context, run_dir: str | Path) -> None:
        self.action_runner = action_runner
        self.env_profile = env_profile
        self.step_context = step_context
        self.run_dir = Path(run_dir)

    def enabled(self) -> bool:
        return self.env_profile.device is not None

    def exec(
        self,
        command: str | list[str],
        *,
        timeout: int | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ):
        device = self.env_profile.device
        if device is None:
            raise StepExecutionError(self.step_context.node_name, "device executor is not configured")
        self._validate_device_config(device)

        if device.protocol in {"mock", "local"}:
            device_cwd = str(self._resolve_device_path(cwd or "."))
            result = self.action_runner.run_device(
                command,
                target=f"{device.protocol}:{device.host or 'device'}",
                step_name=self.step_context.node_name,
                stdout_log=Path(self.step_context.stdout_log_path),
                stderr_log=Path(self.step_context.stderr_log_path),
                cwd=device_cwd,
                env=env,
                timeout=timeout,
            )
        elif device.protocol == "ssh":
            ssh_command = [
                "ssh",
                *self._ssh_option_args(),
                "-p",
                str(device.port),
                f"{device.user}@{device.host}",
                self._render_ssh_command(command, cwd=cwd, env=env),
            ]
            result = self.action_runner.run_device(
                ssh_command,
                target=f"ssh://{device.user}@{device.host}:{device.port}",
                step_name=self.step_context.node_name,
                stdout_log=Path(self.step_context.stdout_log_path),
                stderr_log=Path(self.step_context.stderr_log_path),
                timeout=timeout,
            )
        else:
            raise StepExecutionError(self.step_context.node_name, f"unsupported device protocol: {device.protocol}")

        if result.returncode != 0:
            raise StepExecutionError(self.step_context.node_name, self._failure_message(result, command))
        return result

    def resolve_path(self, path: str) -> Path:
        return self._resolve_device_path(path)

    def resolve_remote_path(self, path: str) -> str:
        device = self.env_profile.device
        if device is None:
            raise StepExecutionError(self.step_context.node_name, "device executor is not configured")
        if device.protocol in {"mock", "local"}:
            return str(self._resolve_device_path(path))

        remote_root = device.remote_root
        normalized = path.strip()
        if not normalized:
            raise StepExecutionError(self.step_context.node_name, "remote path cannot be empty")
        if remote_root:
            return self._join_remote_path(remote_root, normalized)
        if not normalized.startswith("/"):
            raise StepExecutionError(
                self.step_context.node_name,
                "ssh remote path must be absolute when device.remote_root is not configured",
            )
        return self._normalize_remote_absolute_path(normalized)

    def _resolve_device_path(self, path: str) -> Path:
        device_root = self._device_root()
        cleaned = path.lstrip("/")
        return device_root / cleaned

    def _render_ssh_command(self, command: str | list[str], *, cwd: str | None, env: dict[str, str] | None) -> str:
        device = self.env_profile.device
        if device is None:
            raise StepExecutionError(self.step_context.node_name, "device executor is not configured")
        rendered_command = command if isinstance(command, str) else shlex.join(command)
        parts: list[str] = []
        resolved_cwd = self._resolve_remote_cwd(cwd or device.workdir)
        if resolved_cwd:
            parts.append(f"cd {shlex.quote(resolved_cwd)}")
        if env:
            env_exports = " ".join(f"{key}={shlex.quote(str(value))}" for key, value in env.items())
            parts.append(f"export {env_exports}")
        parts.append(rendered_command)
        return " && ".join(parts)

    def _resolve_remote_cwd(self, cwd: str | None) -> str | None:
        if not cwd:
            return None
        return self.resolve_remote_path(cwd)

    def _ssh_option_args(self) -> list[str]:
        device = self.env_profile.device
        if device is None:
            return []
        options = ["BatchMode=yes"]
        if device.connect_timeout is not None:
            options.append(f"ConnectTimeout={device.connect_timeout}")
        options.extend(device.ssh_options)
        args: list[str] = []
        for option in options:
            args.extend(["-o", option])
        return args

    def _validate_device_config(self, device) -> None:
        if device.protocol == "ssh" and not device.host:
            raise StepExecutionError(self.step_context.node_name, "device.host is required for ssh protocol")

    def _failure_message(self, result, command: str | list[str]) -> str:
        detail = (result.stderr or "").strip() or (result.stdout or "").strip()
        return detail or f"device command failed: {command}"

    def _join_remote_path(self, base: str, path: str) -> str:
        base_path = self._normalize_remote_absolute_path(base)
        base_parts = [token for token in base_path.split("/") if token]
        resolved_parts = list(base_parts)
        for token in path.split("/"):
            if token in {"", "."}:
                continue
            if token == "..":
                if len(resolved_parts) > len(base_parts):
                    resolved_parts.pop()
                continue
            resolved_parts.append(token)
        return "/" + "/".join(resolved_parts)

    def _normalize_remote_absolute_path(self, path: str) -> str:
        parts: list[str] = []
        for token in path.split("/"):
            if token in {"", "."}:
                continue
            if token == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(token)
        return "/" + "/".join(parts)

    def _device_root(self) -> Path:
        metadata_root = self.env_profile.metadata.get("device_root")
        if metadata_root:
            root = Path(str(metadata_root))
        else:
            device_name = (self.env_profile.device.host if self.env_profile.device is not None else "") or "mock-device"
            safe_name = device_name.replace("/", "_").replace(":", "_")
            root = self.run_dir / "device_fs" / safe_name
        root.mkdir(parents=True, exist_ok=True)
        return root


class TransferExecutor:
    """Transfer files between host and device or local staging paths."""

    def __init__(self, action_runner, env_profile, step_context, run_dir: str | Path) -> None:
        self.action_runner = action_runner
        self.env_profile = env_profile
        self.step_context = step_context
        self.run_dir = Path(run_dir)
        self.device = DeviceExecutor(action_runner, env_profile, step_context, run_dir)

    def enabled(self) -> bool:
        return self.env_profile.transport is not None

    def put(self, local_path: str, remote_path: str) -> str:
        policy = self.env_profile.transport
        if policy is None:
            raise StepExecutionError(self.step_context.node_name, "transport executor is not configured")
        source = Path(local_path)
        if not source.exists():
            raise StepExecutionError(self.step_context.node_name, f"local transfer source not found: {source}")

        if self.env_profile.device is None or policy.mode in {"local", "mock", "sftp"} and self.env_profile.device.protocol in {"mock", "local"}:
            destination = self.device.resolve_path(remote_path)
            self.action_runner.copy_file(
                source,
                destination,
                action_type="transfer.put",
                target=str(destination),
                step_name=self.step_context.node_name,
                stdout_log=Path(self.step_context.stdout_log_path),
                stderr_log=Path(self.step_context.stderr_log_path),
            )
            return str(destination)

        if policy.mode == "sftp" and self.env_profile.device is not None and self.env_profile.device.protocol == "ssh":
            resolved_remote_path = self.device.resolve_remote_path(remote_path)
            self.device.exec(["mkdir", "-p", self._remote_parent_dir(resolved_remote_path)])
            destination = self._remote_scp_target(resolved_remote_path)
            result = self.action_runner.run_local(
                ["scp", *self.device._ssh_option_args(), "-P", str(self.env_profile.device.port), str(source), destination],
                step_name=self.step_context.node_name,
                stdout_log=Path(self.step_context.stdout_log_path),
                stderr_log=Path(self.step_context.stderr_log_path),
            )
            if result.returncode != 0:
                detail = (result.stderr or "").strip() or (result.stdout or "").strip()
                raise StepExecutionError(self.step_context.node_name, detail or f"transfer.put failed: {source} -> {destination}")
            return resolved_remote_path

        raise StepExecutionError(self.step_context.node_name, f"unsupported transport mode: {policy.mode}")

    def get(self, remote_path: str, local_path: str) -> str:
        policy = self.env_profile.transport
        if policy is None:
            raise StepExecutionError(self.step_context.node_name, "transport executor is not configured")

        destination = Path(local_path)
        if self.env_profile.device is None or policy.mode in {"local", "mock", "sftp"} and self.env_profile.device.protocol in {"mock", "local"}:
            source = self.device.resolve_path(remote_path)
            if not source.exists():
                raise StepExecutionError(self.step_context.node_name, f"remote transfer source not found: {source}")
            self.action_runner.copy_file(
                source,
                destination,
                action_type="transfer.get",
                target=str(source),
                step_name=self.step_context.node_name,
                stdout_log=Path(self.step_context.stdout_log_path),
                stderr_log=Path(self.step_context.stderr_log_path),
            )
            return str(destination)

        if policy.mode == "sftp" and self.env_profile.device is not None and self.env_profile.device.protocol == "ssh":
            resolved_remote_path = self.device.resolve_remote_path(remote_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            source = self._remote_scp_target(resolved_remote_path)
            result = self.action_runner.run_local(
                ["scp", *self.device._ssh_option_args(), "-P", str(self.env_profile.device.port), source, str(destination)],
                step_name=self.step_context.node_name,
                stdout_log=Path(self.step_context.stdout_log_path),
                stderr_log=Path(self.step_context.stderr_log_path),
            )
            if result.returncode != 0:
                detail = (result.stderr or "").strip() or (result.stdout or "").strip()
                raise StepExecutionError(self.step_context.node_name, detail or f"transfer.get failed: {source} -> {destination}")
            return str(destination)

        raise StepExecutionError(self.step_context.node_name, f"unsupported transport mode: {policy.mode}")

    def _remote_parent_dir(self, path: str) -> str:
        parent = path.rsplit("/", 1)[0]
        return parent if parent else "/"

    def _remote_scp_target(self, path: str) -> str:
        device = self.env_profile.device
        if device is None:
            raise StepExecutionError(self.step_context.node_name, "device executor is not configured")
        return f"{device.user}@{device.host}:{shlex.quote(path)}"
