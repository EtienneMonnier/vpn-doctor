"""UI view models.

These classes contain no GTK dependency. They make the UI testable and keep
presentation state independent from backend implementation details.
"""

from __future__ import annotations

from dataclasses import dataclass

from vpn_doctor.models.status import VPNConnectionState, VPNStatus


@dataclass(frozen=True)
class ConnectionStatusViewModel:
    """Presentation model for the connection status area."""

    title: str
    subtitle: str
    css_class: str
    can_connect: bool
    can_disconnect: bool

    @classmethod
    def from_status(cls, status: VPNStatus) -> "ConnectionStatusViewModel":
        state = status.state

        if state == VPNConnectionState.CONNECTED:
            return cls(
                title="Connected",
                subtitle=status.message or "VPN tunnel is active",
                css_class="success",
                can_connect=False,
                can_disconnect=True,
            )

        if state in {VPNConnectionState.CONNECTING, VPNConnectionState.AUTHENTICATING, VPNConnectionState.NEGOTIATING}:
            return cls(
                title="Connecting",
                subtitle=status.message or "VPN connection is being established",
                css_class="warning",
                can_connect=False,
                can_disconnect=True,
            )

        if state == VPNConnectionState.DISCONNECTING:
            return cls(
                title="Disconnecting",
                subtitle=status.message or "VPN connection is being stopped",
                css_class="warning",
                can_connect=False,
                can_disconnect=False,
            )

        if state == VPNConnectionState.FAILED:
            return cls(
                title="Failed",
                subtitle=status.message or "VPN connection failed",
                css_class="error",
                can_connect=True,
                can_disconnect=False,
            )

        return cls(
            title="Disconnected",
            subtitle=status.message or "VPN is not connected",
            css_class="neutral",
            can_connect=True,
            can_disconnect=False,
        )
