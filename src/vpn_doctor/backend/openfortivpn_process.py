"""OpenFortiVPN command construction and process lifecycle."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from vpn_doctor.backend.log_parser import OpenFortiVPNLogParser
from vpn_doctor.backend.process_runner import ProcessRunner
from vpn_doctor.backend.state_machine import ConnectionStateMachine
from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.models.status import VPNConnectionState, VPNStatus

TERMINAL_OR_CONNECTED_STATES = frozenset(
    {
        VPNConnectionState.CONNECTED,
        VPNConnectionState.FAILED,
        VPNConnectionState.DISCONNECTED,
    }
)

ACTIVE_STATES = frozenset(
    {
        VPNConnectionState.CONNECTING,
        VPNConnectionState.AUTHENTICATING,
        VPNConnectionState.NEGOTIATING,
        VPNConnectionState.CONNECTED,
    }
)


@dataclass
class OpenFortiVPNProcess:
    """Manage one openfortivpn process."""

    runner: ProcessRunner = field(default_factory=ProcessRunner)
    parser: OpenFortiVPNLogParser = field(default_factory=OpenFortiVPNLogParser)
    state_machine: ConnectionStateMachine = field(default_factory=ConnectionStateMachine)
    logs: list[str] = field(default_factory=list)
    privilege_command: tuple[str, ...] = ()

    def build_command(self, profile: VPNProfile) -> list[str]:
        command = [
            "openfortivpn",
            f"{profile.host}:{profile.port}",
            # The profile is the only source of truth: never merge options from
            # /etc/openfortivpn/config, which root would otherwise read.
            "-c",
            "/dev/null",
        ]

        if profile.username:
            command.extend(["-u", profile.username])

        if profile.trusted_cert:
            command.extend(["--trusted-cert", profile.trusted_cert])

        if profile.realm:
            command.extend(["--realm", profile.realm])

        if profile.user_cert:
            command.extend(["--user-cert", profile.user_cert])

        if profile.user_key:
            command.extend(["--user-key", profile.user_key])

        return command

    def connect(
        self,
        profile: VPNProfile,
        password: str | None = None,
        on_log: Callable[[str], None] | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        command = [*self.privilege_command, *self.build_command(profile)]

        if dry_run:
            return command

        self.logs.clear()
        self.state_machine.transition(VPNConnectionState.CONNECTING, "Starting openfortivpn")

        stdin_text = None
        if password is not None:
            stdin_text = f"{password}\n"

        self.runner.start(command, on_line=lambda line: self._handle_line(line, on_log), stdin_text=stdin_text)
        return command

    def _handle_line(self, line: str, on_log: Callable[[str], None] | None = None) -> None:
        self.logs.append(line)
        parsed = self.parser.parse(line)
        self.state_machine.apply_log(parsed)

        if on_log is not None:
            on_log(line)

    def _refresh_from_process(self) -> None:
        """Detect an openfortivpn process that exited on its own."""
        if self.runner.process is None or self.runner.is_running:
            return

        if self.state_machine.state in ACTIVE_STATES:
            self.state_machine.transition(
                VPNConnectionState.DISCONNECTED,
                "openfortivpn process exited",
            )

    def disconnect(self) -> None:
        self.state_machine.transition(VPNConnectionState.DISCONNECTING, "Stopping openfortivpn")
        self.runner.terminate(privilege_command=self.privilege_command)
        self.state_machine.transition(VPNConnectionState.DISCONNECTED, "Disconnected")

    def wait_until_terminal_or_connected(self, timeout_seconds: float = 60.0) -> VPNStatus:
        """Wait until connected, failed, disconnected or timeout."""
        deadline = time.monotonic() + timeout_seconds

        while time.monotonic() < deadline:
            status = self.status()
            if status.state in TERMINAL_OR_CONNECTED_STATES:
                return status
            time.sleep(0.1)

        self.state_machine.transition(VPNConnectionState.FAILED, "Connection timeout")
        return self.status()

    def status(self) -> VPNStatus:
        self._refresh_from_process()
        return VPNStatus(
            backend="openfortivpn",
            state=self.state_machine.state,
            message=self.state_machine.last_message,
            suggestion=self.state_machine.suggestion,
        )
