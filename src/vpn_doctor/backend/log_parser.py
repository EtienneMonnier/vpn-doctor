"""OpenFortiVPN log parser.

The parser converts backend text output into normalized status hints.
It deliberately stays conservative: unknown lines are preserved as logs but do
not trigger state changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from vpn_doctor.models.status import VPNConnectionState


class ParsedLogKind(StrEnum):
    """Normalized log categories."""

    UNKNOWN = "unknown"
    CONNECTING = "connecting"
    AUTHENTICATED = "authenticated"
    TUNNEL_UP = "tunnel_up"
    TUNNEL_DOWN = "tunnel_down"
    CERTIFICATE_ERROR = "certificate_error"
    AUTHENTICATION_ERROR = "authentication_error"
    GATEWAY_ERROR = "gateway_error"
    ERROR = "error"


@dataclass(frozen=True)
class ParsedLogLine:
    """Result of parsing a single backend log line."""

    raw: str
    kind: ParsedLogKind
    message: str


class OpenFortiVPNLogParser:
    """Parse known openfortivpn output lines."""

    def parse(self, line: str) -> ParsedLogLine:
        raw = line.strip()
        lowered = raw.lower()

        if not raw:
            return ParsedLogLine(raw=raw, kind=ParsedLogKind.UNKNOWN, message="")

        if "connected to gateway" in lowered:
            return ParsedLogLine(raw=raw, kind=ParsedLogKind.CONNECTING, message=raw)

        if "authenticated" in lowered:
            return ParsedLogLine(raw=raw, kind=ParsedLogKind.AUTHENTICATED, message=raw)

        if "tunnel is up and running" in lowered:
            return ParsedLogLine(raw=raw, kind=ParsedLogKind.TUNNEL_UP, message=raw)

        if "interface ppp" in lowered and "is up" in lowered:
            return ParsedLogLine(raw=raw, kind=ParsedLogKind.TUNNEL_UP, message=raw)

        if "logged out" in lowered or "closed connection to gateway" in lowered:
            return ParsedLogLine(raw=raw, kind=ParsedLogKind.TUNNEL_DOWN, message=raw)

        if "gateway certificate validation failed" in lowered or "trusted-cert" in lowered:
            return ParsedLogLine(raw=raw, kind=ParsedLogKind.CERTIFICATE_ERROR, message=raw)

        if "permission denied" in lowered or "authentication failed" in lowered or "bad credentials" in lowered:
            return ParsedLogLine(raw=raw, kind=ParsedLogKind.AUTHENTICATION_ERROR, message=raw)

        if "could not resolve gateway" in lowered or "could not connect to gateway" in lowered:
            return ParsedLogLine(raw=raw, kind=ParsedLogKind.GATEWAY_ERROR, message=raw)

        if lowered.startswith("error:") or " error:" in lowered:
            return ParsedLogLine(raw=raw, kind=ParsedLogKind.ERROR, message=raw)

        return ParsedLogLine(raw=raw, kind=ParsedLogKind.UNKNOWN, message=raw)

    def parse_state(self, line: str) -> VPNConnectionState:
        """Return normalized VPN state for a single line.

        This compatibility method keeps earlier tests and users stable while the
        richer ParsedLogLine model is introduced.
        """
        parsed = self.parse(line)

        if parsed.kind == ParsedLogKind.CONNECTING:
            return VPNConnectionState.CONNECTING
        if parsed.kind == ParsedLogKind.AUTHENTICATED:
            return VPNConnectionState.AUTHENTICATING
        if parsed.kind == ParsedLogKind.TUNNEL_UP:
            return VPNConnectionState.CONNECTED
        if parsed.kind == ParsedLogKind.TUNNEL_DOWN:
            return VPNConnectionState.DISCONNECTED
        if parsed.kind in {
            ParsedLogKind.CERTIFICATE_ERROR,
            ParsedLogKind.AUTHENTICATION_ERROR,
            ParsedLogKind.GATEWAY_ERROR,
            ParsedLogKind.ERROR,
        }:
            return VPNConnectionState.FAILED

        return VPNConnectionState.UNKNOWN
