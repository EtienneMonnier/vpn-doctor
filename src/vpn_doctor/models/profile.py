"""VPN profile model.

Profiles must not contain secrets.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BackendType(str, Enum):
    OPENFORTIVPN = "openfortivpn"
    WIREGUARD = "wireguard"
    OPENVPN = "openvpn"
    OPENCONNECT = "openconnect"
    STRONGSWAN = "strongswan"


@dataclass(frozen=True)
class VPNProfile:
    name: str
    backend: BackendType
    gateway: str
    port: int | None = None
    username: str | None = None
    realm: str | None = None
    trusted_cert: str | None = None
