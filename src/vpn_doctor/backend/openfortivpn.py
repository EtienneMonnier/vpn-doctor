"""OpenFortiVPN backend.

This module intentionally starts with safe diagnostics only.
Connection management will be implemented in Sprint 2.
"""

from __future__ import annotations

import shutil
import socket
from contextlib import closing

from vpn_doctor.backend.base import VPNBackend
from vpn_doctor.models.diagnostic import DiagnosticItem, DiagnosticReport
from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.models.status import VPNConnectionState, VPNStatus


class OpenFortiVPNBackend(VPNBackend):
    """Backend implementation for openfortivpn."""

    name = "openfortivpn"

    def connect(self, profile: VPNProfile) -> None:
        raise NotImplementedError("OpenFortiVPN connection will be implemented in Sprint 2")

    def disconnect(self) -> None:
        raise NotImplementedError("OpenFortiVPN disconnection will be implemented in Sprint 2")

    def status(self) -> VPNStatus:
        return VPNStatus(
            backend=self.name,
            state=VPNConnectionState.DISCONNECTED,
            message="Connection management is not implemented yet",
        )

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
