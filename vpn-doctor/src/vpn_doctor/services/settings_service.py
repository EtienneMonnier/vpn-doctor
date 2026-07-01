"""Settings and profile loading service."""

from __future__ import annotations

from vpn_doctor.models.profile import VPNProfile


class SettingsService:
    """Load application settings and VPN profiles."""

    def load_default_profile(self) -> VPNProfile:
        """Return a default placeholder profile.

        Do not store real customer VPN data in source code.
        """
        return VPNProfile(
            name="Demo Fortinet VPN",
            backend="openfortivpn",
            host="vpn.example.com",
            port=443,
            username="demo-user",
            trusted_cert=None,
        )
