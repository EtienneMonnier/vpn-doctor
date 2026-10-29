"""Settings and profile loading service."""

from __future__ import annotations

import json
from pathlib import Path

from vpn_doctor.models.profile import VPNProfile

FORBIDDEN_PROFILE_KEYS = frozenset({"password", "passwd", "secret", "token"})


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
        return self.load_configured_profiles() or [self.demo_profile()]

    def load_configured_profiles(self) -> list[VPNProfile]:
        """Load the profiles of profiles.json, without the demo fallback."""
        if not self.profile_path.exists():
            return []

        data = json.loads(self.profile_path.read_text(encoding="utf-8"))
        return [self._profile_from_dict(raw) for raw in data.get("profiles", [])]

    @staticmethod
    def _profile_from_dict(raw: dict) -> VPNProfile:
        if any(key in raw for key in FORBIDDEN_PROFILE_KEYS):
            raise ValueError(
                f"Profile {raw.get('name', '?')!r} contains a secret. "
                "Passwords must not be stored in profile files."
            )
        return VPNProfile(**raw)

    def demo_profile(self) -> VPNProfile:
        return VPNProfile(
            name="Demo Fortinet VPN",
            backend="openfortivpn",
            host="vpn.example.com",
            port=443,
            username="demo-user",
            trusted_cert=None,
        )
