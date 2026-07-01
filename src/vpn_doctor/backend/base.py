"""Base VPN backend interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from vpn_doctor.models.diagnostic import DiagnosticReport
from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.models.status import VPNStatus


class VPNBackend(ABC):
    """Common interface for all VPN backends."""

    name: str

    @abstractmethod
    def connect(self, profile: VPNProfile) -> None:
        """Connect using the supplied profile."""

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect the active VPN session."""

    @abstractmethod
    def status(self) -> VPNStatus:
        """Return current backend status."""

    @abstractmethod
    def diagnose(self, profile: VPNProfile) -> DiagnosticReport:
        """Run backend-specific diagnostics."""
