"""OpenFortiVPN backend."""

from __future__ import annotations

import shutil
import socket
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass, field

from vpn_doctor.backend.base import VPNBackend
from vpn_doctor.backend.command import BackendCommand
from vpn_doctor.backend.log_parser import OpenFortiVPNLogParser
from vpn_doctor.backend.openfortivpn_process import OpenFortiVPNProcess
from vpn_doctor.models.diagnostic import DiagnosticItem, DiagnosticReport
from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.models.status import VPNStatus


@dataclass
class OpenFortiVPNBackend(VPNBackend):
    """Backend implementation for openfortivpn."""

    name: str = "openfortivpn"
    process: OpenFortiVPNProcess = field(default_factory=OpenFortiVPNProcess)

    def build_command(self, profile: VPNProfile) -> BackendCommand:
        """Build the openfortivpn command without starting a process."""
        return BackendCommand(argv=self.process.build_command(profile))

    def connect(
        self,
        profile: VPNProfile,
        password: str | None = None,
        on_log: Callable[[str], None] | None = None,
        dry_run: bool = False,
        wait: bool = False,
        timeout_seconds: float = 60.0,
    ) -> list[str] | VPNStatus:
        """Start openfortivpn or return the command when dry_run is enabled."""
        command = self.process.connect(profile, password=password, on_log=on_log, dry_run=dry_run)

        if dry_run:
            return command

        if wait:
            return self.process.wait_until_terminal_or_connected(timeout_seconds=timeout_seconds)

        return command

    def disconnect(self) -> None:
        """Disconnect the active VPN session."""
        self.process.disconnect()

    def status(self) -> VPNStatus:
        """Return current backend status."""
        return self.process.status()

    def diagnose(self, profile: VPNProfile) -> DiagnosticReport:
        items: list[DiagnosticItem] = []

        binary_found = shutil.which("openfortivpn") is not None
        items.append(
            DiagnosticItem(
                name="openfortivpn binary",
                success=binary_found,
                message="openfortivpn is installed" if binary_found else "openfortivpn is missing",
                suggestion=None
                if binary_found
                else "Install openfortivpn using your distribution package manager",
            )
        )

        gateway_ok = self._is_gateway_reachable(profile.host, profile.port)
        items.append(
            DiagnosticItem(
                name="gateway reachability",
                success=gateway_ok,
                message=f"{profile.host}:{profile.port} is reachable"
                if gateway_ok
                else f"{profile.host}:{profile.port} is unreachable",
                suggestion=None
                if gateway_ok
                else "Check hostname, port, firewall or network connectivity",
            )
        )

        return DiagnosticReport.from_items("OpenFortiVPN basic diagnostics", items)

    @staticmethod
    def _is_gateway_reachable(host: str, port: int, timeout: float = 3.0) -> bool:
        try:
            with closing(socket.create_connection((host, port), timeout=timeout)):
                return True
        except OSError:
            return False
