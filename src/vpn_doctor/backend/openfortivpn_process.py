"""OpenFortiVPN command construction and process lifecycle."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from vpn_doctor.backend.log_parser import OpenFortiVPNLogParser
from vpn_doctor.backend.process_runner import ProcessRunner
from vpn_doctor.backend.state_machine import ConnectionStateMachine
from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.models.status import VPNConnectionState, VPNStatus


@dataclass
class OpenFortiVPNProcess:
    """Manage one openfortivpn process."""

    runner: ProcessRunner = field(default_factory=ProcessRunner)
    parser: OpenFortiVPNLogParser = field(default_factory=OpenFortiVPNLogParser)
    state_machine: ConnectionStateMachine = field(default_factory=ConnectionStateMachine)
    logs: list[str] = field(default_factory=list)

    def build_command(self, profile: VPNProfile) -> list[str]:
        command = [
            "openfortivpn",
            f"{profile.host}:{profile.port}",
        ]

        if profile.username:
            command.extend(["-u", profile.username])

        if profile.trusted_cert:
            command.extend(["--trusted-cert", profile.trusted_cert])

        if profile.realm:
            command.extend(["--realm", profile.realm])

        return command

    def connect(
        self,
        profile: VPNProfile,
        password: str | None = None,
        on_log: Callable[[str], None] | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        command = self.build_command(profile)

        if dry_run:
            return command

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

    def disconnect(self) -> None:
        self.state_machine.transition(VPNConnectionState.DISCONNECTING, "Stopping openfortivpn")
        self.runner.terminate()
        self.state_machine.transition(VPNConnectionState.DISCONNECTED, "Disconnected")

    def status(self) -> VPNStatus:
        return VPNStatus(
            backend="openfortivpn",
            state=self.state_machine.state,
            message=self.state_machine.last_message,
        )
