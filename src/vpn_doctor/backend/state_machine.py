"""Connection state machine for VPN backends."""

from __future__ import annotations

from dataclasses import dataclass

from vpn_doctor.backend.log_parser import ParsedLogKind, ParsedLogLine
from vpn_doctor.models.status import VPNConnectionState


@dataclass
class ConnectionStateMachine:
    """Small deterministic state machine for backend status."""

    state: VPNConnectionState = VPNConnectionState.DISCONNECTED
    last_message: str | None = None

    def transition(self, new_state: VPNConnectionState, message: str | None = None) -> None:
        self.state = new_state
        self.last_message = message

    def apply_log(self, parsed: ParsedLogLine) -> VPNConnectionState:
        """Update state from a parsed backend log line."""
        self.last_message = parsed.message or self.last_message

        if parsed.kind == ParsedLogKind.CONNECTING:
            self.state = VPNConnectionState.CONNECTING

        elif parsed.kind == ParsedLogKind.AUTHENTICATED:
            self.state = VPNConnectionState.AUTHENTICATING

        elif parsed.kind == ParsedLogKind.TUNNEL_UP:
            self.state = VPNConnectionState.CONNECTED

        elif parsed.kind == ParsedLogKind.TUNNEL_DOWN:
            self.state = VPNConnectionState.DISCONNECTED

        elif parsed.kind in {
            ParsedLogKind.CERTIFICATE_ERROR,
            ParsedLogKind.AUTHENTICATION_ERROR,
            ParsedLogKind.GATEWAY_ERROR,
            ParsedLogKind.ERROR,
        }:
            self.state = VPNConnectionState.FAILED

        return self.state
