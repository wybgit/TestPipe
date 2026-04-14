from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from testpipe.core.exceptions import StepExecutionError
from testpipe.infra import ActionResult, DeviceExecutor, TransferExecutor
from testpipe.spec import EnvProfile, FrameworkConfig


class _FakeActionRunner:
    def __init__(self) -> None:
        self.device_calls: list[dict[str, object]] = []
        self.local_calls: list[dict[str, object]] = []

    def run_device(self, command, **kwargs):
        self.device_calls.append({"command": command, **kwargs})
        return ActionResult(
            action_type="device.exec",
            target=str(kwargs.get("target", "")),
            command=command,
            returncode=0,
            stdout="",
            stderr="",
        )

    def run_local(self, command, **kwargs):
        self.local_calls.append({"command": command, **kwargs})
        return ActionResult(
            action_type="host.exec",
            target="local",
            command=command,
            returncode=0,
            stdout="",
            stderr="",
        )


class _FailingActionRunner(_FakeActionRunner):
    def run_local(self, command, **kwargs):
        self.local_calls.append({"command": command, **kwargs})
        return ActionResult(
            action_type="host.exec",
            target="local",
            command=command,
            returncode=1,
            stdout="ATC run failed: invalid option",
            stderr="",
        )


class ExecutorHardeningTest(unittest.TestCase):
    def _step_context(self, tmp_dir: str):
        return SimpleNamespace(
            node_name="test_step",
            stdout_log_path=str(Path(tmp_dir) / "stdout.log"),
            stderr_log_path=str(Path(tmp_dir) / "stderr.log"),
        )

    def test_env_profile_parses_ssh_runtime_fields(self) -> None:
        profile = EnvProfile.from_dict(
            {
                "device": {
                    "protocol": "ssh",
                    "host": "192.168.10.20",
                    "port": 2222,
                    "user": "tester",
                    "workdir": "workspace",
                    "remote_root": "/srv/testpipe",
                    "ssh_options": ["StrictHostKeyChecking=no", "UserKnownHostsFile=/dev/null"],
                    "connect_timeout": 15,
                },
                "transport": {"mode": "sftp"},
            }
        )
        self.assertEqual(profile.device.workdir, "workspace")
        self.assertEqual(profile.device.remote_root, "/srv/testpipe")
        self.assertEqual(profile.device.ssh_options, ["StrictHostKeyChecking=no", "UserKnownHostsFile=/dev/null"])
        self.assertEqual(profile.device.connect_timeout, 15)

    def test_device_executor_builds_ssh_command_with_root_workdir_and_options(self) -> None:
        runner = _FakeActionRunner()
        env_profile = EnvProfile.from_dict(
            {
                "device": {
                    "protocol": "ssh",
                    "host": "192.168.10.20",
                    "port": 2222,
                    "user": "tester",
                    "workdir": "workspace",
                    "remote_root": "/srv/testpipe",
                    "ssh_options": ["StrictHostKeyChecking=no", "UserKnownHostsFile=/dev/null"],
                    "connect_timeout": 15,
                },
                "transport": {"mode": "sftp"},
            }
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            executor = DeviceExecutor(runner, env_profile, self._step_context(tmp_dir), tmp_dir)
            executor.exec(["python3", "run.py"], env={"CASE_NAME": "case 1"})

        self.assertEqual(len(runner.device_calls), 1)
        command = runner.device_calls[0]["command"]
        self.assertEqual(
            command,
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=15",
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                "-p",
                "2222",
                "tester@192.168.10.20",
                "cd /srv/testpipe/workspace && export CASE_NAME='case 1' && python3 run.py",
            ],
        )

    def test_device_executor_resolve_remote_path_stays_within_remote_root(self) -> None:
        runner = _FakeActionRunner()
        env_profile = EnvProfile.from_dict(
            {
                "device": {
                    "protocol": "ssh",
                    "host": "192.168.10.20",
                    "remote_root": "/srv/testpipe",
                },
                "transport": {"mode": "sftp"},
            }
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            executor = DeviceExecutor(runner, env_profile, self._step_context(tmp_dir), tmp_dir)
            self.assertEqual(executor.resolve_remote_path("inputs/a.txt"), "/srv/testpipe/inputs/a.txt")
            self.assertEqual(executor.resolve_remote_path("../escape.txt"), "/srv/testpipe/escape.txt")

    def test_transfer_executor_ssh_put_creates_remote_parent_before_scp(self) -> None:
        runner = _FakeActionRunner()
        env_profile = EnvProfile.from_dict(
            {
                "device": {
                    "protocol": "ssh",
                    "host": "192.168.10.20",
                    "port": 2222,
                    "user": "tester",
                    "remote_root": "/srv/testpipe",
                    "ssh_options": ["StrictHostKeyChecking=no"],
                    "connect_timeout": 8,
                },
                "transport": {"mode": "sftp"},
            }
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = Path(tmp_dir) / "payload.txt"
            source.write_text("demo", encoding="utf-8")
            executor = TransferExecutor(runner, env_profile, self._step_context(tmp_dir), tmp_dir)
            remote_path = executor.put(str(source), "/inputs/payload.txt")

        self.assertEqual(remote_path, "/srv/testpipe/inputs/payload.txt")
        self.assertEqual(len(runner.device_calls), 1)
        self.assertEqual(
            runner.device_calls[0]["command"],
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=8",
                "-o",
                "StrictHostKeyChecking=no",
                "-p",
                "2222",
                "tester@192.168.10.20",
                "mkdir -p /srv/testpipe/inputs",
            ],
        )
        self.assertEqual(
            runner.local_calls[0]["command"],
            [
                "scp",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=8",
                "-o",
                "StrictHostKeyChecking=no",
                "-P",
                "2222",
                str(source),
                "tester@192.168.10.20:/srv/testpipe/inputs/payload.txt",
            ],
        )

    def test_transfer_executor_requires_absolute_path_without_remote_root(self) -> None:
        runner = _FakeActionRunner()
        env_profile = EnvProfile.from_dict(
            {
                "device": {
                    "protocol": "ssh",
                    "host": "192.168.10.20",
                },
                "transport": {"mode": "sftp"},
            }
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = Path(tmp_dir) / "payload.txt"
            source.write_text("demo", encoding="utf-8")
            executor = TransferExecutor(runner, env_profile, self._step_context(tmp_dir), tmp_dir)
            with self.assertRaisesRegex(StepExecutionError, "must be absolute"):
                executor.put(str(source), "inputs/payload.txt")

    def test_host_executor_failure_prefers_command_output_detail(self) -> None:
        runner = _FailingActionRunner()
        with tempfile.TemporaryDirectory() as tmp_dir:
            step_context = self._step_context(tmp_dir)
            # Reuse HostExecutor behavior through direct import to avoid adding another helper.
            from testpipe.infra.executors import HostExecutor

            host_executor = HostExecutor(runner, step_context)
            with self.assertRaisesRegex(StepExecutionError, "ATC run failed: invalid option"):
                host_executor.exec(["bash", "-lc", "false"])

    def test_framework_config_resolves_enabled_named_env(self) -> None:
        config = FrameworkConfig.from_dict(
            {
                "testpipe": {
                    "default_env": "local",
                    "envs": {
                        "local": {"enabled": True, "host": {"mode": "local"}},
                        "conda_ci": {"enabled": True, "host": {"mode": "conda", "conda_env": "aitest"}},
                    },
                }
            }
        )
        profile = config.resolve_env_profile("conda_ci")
        self.assertEqual(profile.host.mode, "conda")
        self.assertEqual(profile.host.conda_env, "aitest")

    def test_framework_config_rejects_disabled_env(self) -> None:
        config = FrameworkConfig.from_dict(
            {
                "testpipe": {
                    "default_env": "local",
                    "envs": {
                        "local": {"enabled": True, "host": {"mode": "local"}},
                        "docker_ci": {"enabled": False, "host": {"mode": "docker", "docker_image": "testpipe:latest"}},
                    },
                }
            }
        )
        with self.assertRaisesRegex(ValueError, "disabled"):
            config.resolve_env_profile("docker_ci")

    def test_host_executor_wraps_command_for_conda_mode(self) -> None:
        runner = _FakeActionRunner()
        env_profile = EnvProfile.from_dict({"host": {"mode": "conda", "conda_env": "aitest"}})
        with tempfile.TemporaryDirectory() as tmp_dir:
            step_context = self._step_context(tmp_dir)
            from testpipe.infra.executors import HostExecutor

            host_executor = HostExecutor(runner, step_context, env_profile)
            host_executor.exec(["python3", "-V"], cwd=tmp_dir)

        self.assertEqual(
            runner.local_calls[0]["command"],
            ["conda", "run", "-n", "aitest", "bash", "-lc", "python3 -V"],
        )
        self.assertEqual(runner.local_calls[0]["cwd"], tmp_dir)


if __name__ == "__main__":
    unittest.main()
