"""Backend manager.

The manager is the single entry point used by controllers and, later, the GUI.
"""

from __future__ import annotations

from dataclasses import dataclass

from vpn_doctor.backend.registry import BackendRegistry
from vpn_doctor.models.diagnostic import DiagnosticReport
from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.models.status import VPNStatus


@dataclass
class BackendManager:
    """Coordinate backend access."""

    registry: BackendRegistry

    def diagnose(self, profile: VPNProfile) -> DiagnosticReport:
        return self.registry.get(profile.backend).diagnose(profile)

    def status(self, profile: VPNProfile) -> VPNStatus:
        return self.registry.get(profile.backend).status()

    def connect(self, profile: VPNProfile, **kwargs) -> object:
        return self.registry.get(profile.backend).connect(profile, **kwargs)

    def disconnect(self, profile: VPNProfile) -> object:
        return self.registry.get(profile.backend).disconnect()

    def available_backends(self) -> list[str]:
        return self.registry.names()
