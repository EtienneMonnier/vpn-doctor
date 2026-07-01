"""OpenFortiVPN process lifecycle management."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from vpn_doctor.backend.openfortivpn_parser import OpenFortiVPNLogParser
from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.models.status import VPNConnectionState, VPNStatus
from vpn_doctor.services.process_runner import ManagedProcess, ProcessRunner

LOGGER = logging.getLogger(__name__)


@dataclass
class OpenFortiVPNProcess:
    """Manage one openfortivpn process."""

    runner: ProcessRunner = field(default_factory=ProcessRunner)
    parser: OpenFortiVPNLogParser = field(default_factory=OpenFortiVPNLogParser)
    process: ManagedProcess | None = None
    status: VPNStatus = field(
        default_factory=lambda: VPNStatus(
            backend="openfortivpn",
            state=VPNConnectionState.DISCONNECTED,
            message="Not connected",
        )
    )

    def start(
        self,
        argv: list[str],
        profile: VPNProfile,
        *,
        password: str | None = None,
        dry_run: bool = False,
        foreground: bool = False,
    ) -> VPNStatus:
        """Start openfortivpn.

        `dry_run=True` validates the command and updates status without launching anything.
        This is useful for early CLI and tests.
        """
        if dry_run:
            self.status = VPNStatus(
                backend="openfortivpn",
                state=VPNConnectionState.DISCONNECTED,
                message="Dry run: command validated, process not started",
            )
            return self.status

        stdin_text = f"{password}\n" if password is not None else None
        self.process = self.runner.start(argv, stdin_text=stdin_text)
        self.status = VPNStatus(
            backend="openfortivpn",
            state=VPNConnectionState.CONNECTING,
            message=f"Starting profile '{profile.name}'",
        )

        if foreground:
            return self.follow_until_exit()

        return self.status

    def follow_until_exit(self) -> VPNStatus:
        """Read process output until it exits."""
        if self.process is None:
            return self.status

        if self.process.stdout is not None:
            for line in self.process.stdout:
                self.handle_log_line(line.rstrip())

        exit_code = self.process.wait()
        if exit_code != 0 and self.status.state != VPNConnectionState.FAILED:
            self.status = VPNStatus(
                backend="openfortivpn",
                state=VPNConnectionState.FAILED,
                message=f"openfortivpn exited with code {exit_code}",
            )
        elif self.status.state != VPNConnectionState.FAILED:
            self.status = VPNStatus(
                backend="openfortivpn",
                state=VPNConnectionState.DISCONNECTED,
                message="openfortivpn exited",
            )

        return self.status

    def handle_log_line(self, line: str) -> VPNStatus:
        """Update status from one openfortivpn log line."""
        LOGGER.info("openfortivpn: %s", line)
        parsed = self.parser.parse(line)
        if parsed.state is not None:
            self.status = VPNStatus(
                backend="openfortivpn",
                state=parsed.state,
                message=line,
            )
        return self.status

    def stop(self, timeout: float = 10.0) -> VPNStatus:
        """Stop the running process gracefully."""
        if self.process is None or self.process.poll() is not None:
            self.status = VPNStatus(
                backend="openfortivpn",
                state=VPNConnectionState.DISCONNECTED,
                message="No active openfortivpn process",
            )
            return self.status

        self.status = VPNStatus(
            backend="openfortivpn",
            state=VPNConnectionState.DISCONNECTING,
            message="Stopping openfortivpn",
        )
        self.process.terminate()

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                self.status = VPNStatus(
                    backend="openfortivpn",
                    state=VPNConnectionState.DISCONNECTED,
                    message="openfortivpn stopped",
                )
                return self.status
            time.sleep(0.1)

        self.process.kill()
        self.status = VPNStatus(
            backend="openfortivpn",
            state=VPNConnectionState.DISCONNECTED,
            message="openfortivpn killed after timeout",
        )
        return self.status
