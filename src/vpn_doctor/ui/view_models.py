"""UI view models.

These classes contain no GTK dependency. They make the UI testable and keep
presentation state independent from backend implementation details.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from vpn_doctor.i18n import _
from vpn_doctor.models.status import VPNConnectionState, VPNStatus


@dataclass(frozen=True)
class ConnectionStatusViewModel:
    """Presentation model for the connection status area."""

    title: str
    subtitle: str
    css_class: str
    can_connect: bool
    can_disconnect: bool
    pill: str = ""

    @classmethod
    def from_status(cls, status: VPNStatus) -> ConnectionStatusViewModel:
        state = status.state

        if status.prompt:
            return cls(
                title=_("Waiting for you"),
                subtitle=status.prompt,
                css_class="warning",
                can_connect=False,
                can_disconnect=True,
                pill=_("⌨ INPUT"),
            )

        if state == VPNConnectionState.CONNECTED:
            return cls(
                title=_("Connected"),
                subtitle=status.message or _("VPN tunnel is active"),
                css_class="success",
                can_connect=False,
                can_disconnect=True,
                pill=_("● ONLINE"),
            )

        if state in {VPNConnectionState.CONNECTING, VPNConnectionState.AUTHENTICATING, VPNConnectionState.NEGOTIATING}:
            return cls(
                title=_("Connecting"),
                subtitle=status.message or _("VPN connection is being established"),
                css_class="warning",
                can_connect=False,
                can_disconnect=True,
                pill=_("◐ LINKING"),
            )

        if state == VPNConnectionState.DISCONNECTING:
            return cls(
                title=_("Disconnecting"),
                subtitle=status.message or _("VPN connection is being stopped"),
                css_class="warning",
                can_connect=False,
                can_disconnect=False,
                pill=_("◑ CLOSING"),
            )

        if state == VPNConnectionState.FAILED:
            return cls(
                title=_("Failed"),
                subtitle=status.suggestion or status.message or _("VPN connection failed"),
                css_class="error",
                can_connect=True,
                can_disconnect=False,
                pill=_("✕ FAILURE"),
            )

        return cls(
            title=_("Disconnected"),
            subtitle=status.message or _("VPN is not connected"),
            css_class="neutral",
            can_connect=True,
            can_disconnect=False,
                pill=_("○ OFFLINE"),
        )


def format_elapsed(seconds: float) -> str:
    """Format a duration as HH:MM:SS."""
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


@dataclass
class ConnectionTimer:
    """Track how long the tunnel has been connected.

    The caller passes the current monotonic time so the class stays
    deterministic and easy to test.
    """

    _connected_since: float | None = field(default=None, init=False)

    def update(self, state: VPNConnectionState, now: float) -> str | None:
        """Return the elapsed connected time, or None when not connected."""
        if state != VPNConnectionState.CONNECTED:
            self._connected_since = None
            return None

        if self._connected_since is None:
            self._connected_since = now

        return format_elapsed(now - self._connected_since)
