"""Settings and profile loading service."""

from __future__ import annotations

import json
from pathlib import Path

from vpn_doctor.models.profile import VPNProfile


class SettingsService:
    """Load application settings and VPN profiles."""

    def __init__(self, profile_path: Path | None = None) -> None:
        self.profile_path = profile_path or Path.home() / ".config" / "vpn-doctor" / "profiles.json"

    def load_default_profile(self) -> VPNProfile:
        """Return the default profile.

        If no user configuration exists, return a safe demo profile.
        """
        profiles = self.load_profiles()
        return profiles[0]

    def load_profiles(self) -> list[VPNProfile]:
        """Load user profiles or return a safe demo profile."""
        if not self.profile_path.exists():
            return [self._demo_profile()]

        data = json.loads(self.profile_path.read_text(encoding="utf-8"))
        raw_profiles = data.get("profiles", [])
        if not raw_profiles:
            return [self._demo_profile()]

        return [VPNProfile(**raw) for raw in raw_profiles]

    def _demo_profile(self) -> VPNProfile:
        return VPNProfile(
            name="Demo Fortinet VPN",
            backend="openfortivpn",
            host="vpn.example.com",
            port=443,
            username="demo-user",
            trusted_cert=None,
        )
