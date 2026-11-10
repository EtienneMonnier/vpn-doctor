"""VPN status models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class VPNConnectionState(StrEnum):
    """Normalized VPN connection state."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    NEGOTIATING = "negotiating"
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
    suggestion: str | None = None
    prompt: str | None = None
    vpn_ip: str | None = None
    connected_seconds: int | None = None

    def to_dict(self) -> dict:
        return {
            "backend": self.backend,
            "state": str(self.state),
            "message": self.message,
            "suggestion": self.suggestion,
            "prompt": self.prompt,
            "vpn_ip": self.vpn_ip,
            "connected_seconds": self.connected_seconds,
        }
