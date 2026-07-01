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
    host: str
    port: int
    username: str | None = None
    trusted_cert: str | None = None
    realm: str | None = None
