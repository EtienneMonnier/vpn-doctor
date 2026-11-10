"""Base VPN backend interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from vpn_doctor.models.diagnostic import DiagnosticReport
from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.models.status import VPNStatus


class VPNBackend(ABC):
    """Common interface for all VPN backends."""

    name: str
    # True when the backend collects passwords itself (e.g. NetworkManager
    # through the GNOME secret agent), so the UI must not ask for one.
    manages_secrets: bool = False

    @abstractmethod
    def connect(self, profile: VPNProfile) -> None:
        """Connect using the supplied profile."""

    @abstractmethod
    def disconnect(self, profile: VPNProfile | None = None) -> None:
        """Disconnect the active VPN session."""

    @abstractmethod
    def status(self, profile: VPNProfile | None = None) -> VPNStatus:
        """Return the status of the profile, or of the backend session."""

    @abstractmethod
    def diagnose(self, profile: VPNProfile) -> DiagnosticReport:
        """Run backend-specific diagnostics."""

    def list_profiles(self) -> list[VPNProfile]:
        """Return profiles the backend discovers by itself, e.g. NetworkManager."""
        return []

    def answer_prompt(self, answer: str) -> None:
        """Answer an interactive backend prompt, such as a two-factor token."""
        raise NotImplementedError(f"{self.name} does not support interactive prompts")
