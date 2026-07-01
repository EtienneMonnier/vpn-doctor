"""OpenFortiVPN backend."""

from __future__ import annotations

import shutil
import socket
from contextlib import closing
from dataclasses import dataclass, field

from vpn_doctor.backend.base import VPNBackend
from vpn_doctor.backend.openfortivpn_parser import OpenFortiVPNLogParser
from vpn_doctor.backend.openfortivpn_process import OpenFortiVPNProcess
from vpn_doctor.models.diagnostic import DiagnosticItem, DiagnosticReport, DiagnosticSeverity
from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.models.status import VPNConnectionState, VPNStatus


@dataclass(frozen=True)
class OpenFortiVPNCommand:
    """Command parts for openfortivpn.

    This object must never contain passwords.
    """

    argv: list[str]


@dataclass
class OpenFortiVPNBackend(VPNBackend):
    """Backend implementation for openfortivpn."""

    name = "openfortivpn"
    process: OpenFortiVPNProcess = field(default_factory=OpenFortiVPNProcess)
    log_parser: OpenFortiVPNLogParser = field(default_factory=OpenFortiVPNLogParser)

    def build_command(self, profile: VPNProfile) -> OpenFortiVPNCommand:
        """Build an openfortivpn command without secrets."""
        argv = ["openfortivpn", f"{profile.host}:{profile.port}"]

        if profile.username:
            argv.extend(["-u", profile.username])

        if profile.trusted_cert:
            argv.extend(["--trusted-cert", profile.trusted_cert])

        if profile.realm:
            argv.extend(["--realm", profile.realm])

        return OpenFortiVPNCommand(argv=argv)

    def connect(
        self,
        profile: VPNProfile,
        *,
        password: str | None = None,
        dry_run: bool = False,
        foreground: bool = False,
    ) -> VPNStatus:
        command = self.build_command(profile)
        return self.process.start(
            command.argv,
            profile,
            password=password,
            dry_run=dry_run,
            foreground=foreground,
        )

    def disconnect(self) -> VPNStatus:
        return self.process.stop()

    def status(self) -> VPNStatus:
        return self.process.status

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
                severity=DiagnosticSeverity.ERROR if not binary_found else DiagnosticSeverity.INFO,
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
                severity=DiagnosticSeverity.ERROR if not gateway_ok else DiagnosticSeverity.INFO,
            )
        )

        command = self.build_command(profile)
        command_line = " ".join(command.argv).lower()
        items.append(
            DiagnosticItem(
                name="command build",
                success="password" not in command_line and "vpnpass" not in command_line,
                message="openfortivpn command can be built without embedding secrets",
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
