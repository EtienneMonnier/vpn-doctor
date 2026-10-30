"""VPN profile model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VPNProfile:
    """VPN profile definition.

    Secrets must never be stored in this model.
    Passwords belong in GNOME Keyring / Secret Service.
    """

    name: str
    backend: str
    # Optional for NetworkManager connections, where the gateway lives in NM.
    host: str = ""
    port: int = 0
    username: str | None = None
    trusted_cert: str | None = None
    realm: str | None = None
    # Paths to a client certificate and its private key, never their content.
    user_cert: str | None = None
    user_key: str | None = None
    # NetworkManager connection identity and VPN type (openvpn, wireguard...).
    nm_uuid: str | None = None
    vpn_type: str | None = None

    def to_dict(self) -> dict:
        """Public description: no user name, no certificate path, no secret."""
        return {
            "name": self.name,
            "backend": self.backend,
            "managed_by": "networkmanager" if self.nm_uuid else "vpn-doctor",
            "vpn_type": self.vpn_type,
            "host": self.host or None,
            "port": self.port or None,
        }
