"""VPN status models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class VPNConnectionState(StrEnum):
    """Normalized VPN connection state."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class VPNStatus:
    """Current VPN status."""

    backend: str
    state: VPNConnectionState
    message: str | None = None
    vpn_ip: str | None = None
    connected_seconds: int | None = None
