"""OpenFortiVPN backend.

Sprint 2 keeps this backend safe: diagnostics, command construction and log parsing
are implemented, while real connection lifecycle will be expanded carefully.
"""

from __future__ import annotations

import shutil
import socket
from contextlib import closing
from dataclasses import dataclass

from vpn_doctor.backend.base import VPNBackend
from vpn_doctor.models.diagnostic import DiagnosticItem, DiagnosticReport, DiagnosticSeverity
from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.models.status import VPNConnectionState, VPNStatus


@dataclass(frozen=True)
class OpenFortiVPNCommand:
    """Command parts for openfortivpn.

    This object must never contain passwords.
    """

    argv: list[str]


class OpenFortiVPNLogParser:
    """Parse openfortivpn logs into normalized states."""

    def parse_state(self, line: str) -> VPNConnectionState | None:
        normalized = line.lower()

        if "connected to gateway" in normalized:
            return VPNConnectionState.CONNECTING
        if "authenticated" in normalized:
            return VPNConnectionState.AUTHENTICATING
        if "remote gateway has allocated a vpn" in normalized:
            return VPNConnectionState.CONFIGURING
        if "tunnel is up and running" in normalized:
            return VPNConnectionState.CONNECTED
        if "gateway certificate validation failed" in normalized:
            return VPNConnectionState.FAILED
        if "could not authenticate" in normalized:
            return VPNConnectionState.FAILED
        if "connection terminated" in normalized:
            return VPNConnectionState.DISCONNECTED

        return None


class OpenFortiVPNBackend(VPNBackend):
    """Backend implementation for openfortivpn."""

    name = "openfortivpn"

    def __init__(self) -> None:
        self._status = VPNStatus(
            backend=self.name,
            state=VPNConnectionState.DISCONNECTED,
            message="Not connected",
        )
        self.log_parser = OpenFortiVPNLogParser()

    def build_command(self, profile: VPNProfile) -> OpenFortiVPNCommand:
        """Build an openfortivpn command without secrets."""
        argv = ["openfortivpn", f"{profile.host}:{profile.port}"]

        if profile.username:
            argv.extend(["-u", profile.username])

        if profile.trusted_cert:
            argv.extend(["--trusted-cert", profile.trusted_cert])

        return OpenFortiVPNCommand(argv=argv)

    def connect(self, profile: VPNProfile) -> None:
        raise NotImplementedError("Real OpenFortiVPN connection is planned for Sprint 2 implementation")

    def disconnect(self) -> None:
        raise NotImplementedError("Real OpenFortiVPN disconnection is planned for Sprint 2 implementation")

    def status(self) -> VPNStatus:
        return self._status

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
        items.append(
            DiagnosticItem(
                name="command build",
                success="VPNpass" not in " ".join(command.argv),
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
