"""Backend manager.

The manager is the only service that selects a backend for a profile. The UI and
controllers should not instantiate backend implementations directly.
"""

from __future__ import annotations

from vpn_doctor.backend.base import VPNBackend
from vpn_doctor.backend.openfortivpn import OpenFortiVPNBackend
from vpn_doctor.backend.registry import BackendRegistry
from vpn_doctor.models.diagnostic import DiagnosticReport
from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.models.status import VPNStatus


class BackendManager:
    """Select and operate VPN backends."""

    def __init__(self, registry: BackendRegistry | None = None) -> None:
        self.registry = registry or BackendRegistry()
        if registry is None:
            self.registry.register(OpenFortiVPNBackend())

    def backend_for_profile(self, profile: VPNProfile) -> VPNBackend:
        return self.registry.get(profile.backend)

    def connect(
        self,
        profile: VPNProfile,
        *,
        password: str | None = None,
        dry_run: bool = False,
        foreground: bool = False,
    ) -> VPNStatus:
        backend = self.backend_for_profile(profile)
        return backend.connect(
            profile,
            password=password,
            dry_run=dry_run,
            foreground=foreground,
        )

    def disconnect(self, profile: VPNProfile) -> VPNStatus:
        backend = self.backend_for_profile(profile)
        return backend.disconnect()

    def status(self, profile: VPNProfile) -> VPNStatus:
        backend = self.backend_for_profile(profile)
        return backend.status()

    def diagnose(self, profile: VPNProfile) -> DiagnosticReport:
        backend = self.backend_for_profile(profile)
        return backend.diagnose(profile)
