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
    PRIVILEGE_ERROR = "privilege_error"
    ERROR = "error"


# Messages verified against openfortivpn 1.23 and polkit's pkexec.
PRIVILEGE_ERROR_MARKERS = (
    "not spawned with root privileges",
    "error executing command as another user",
)

AUTHENTICATION_ERROR_MARKERS = (
    "could not authenticate to gateway",
    "could not authenticate to the gateway",
    "permission denied",
    "authentication failed",
    "bad credentials",
    "no password given",
)

GATEWAY_ERROR_MARKERS = (
    "could not resolve gateway",
    "could not connect to gateway",
    "getaddrinfo:",
    "connection refused",
    "no route to host",
    "network is unreachable",
)

FAILURE_SUGGESTIONS: dict[ParsedLogKind, str] = {
    ParsedLogKind.AUTHENTICATION_ERROR: (
        "The gateway refused the login. Check the password, the username and the realm. "
        "If they are correct, ask the administrator whether tunnel mode is allowed for "
        "this account."
    ),
    ParsedLogKind.CERTIFICATE_ERROR: (
        "The gateway certificate is not trusted. Verify its fingerprint with your "
        "administrator, then add it to the profile as trusted_cert."
    ),
    ParsedLogKind.GATEWAY_ERROR: (
        "The gateway cannot be reached. Check the host name, the port, your Internet "
        "connection and any firewall in between."
    ),
    ParsedLogKind.PRIVILEGE_ERROR: (
        "openfortivpn needs administrator privileges to create the PPP interface "
        "and routes. Accept the administrator authentication prompt, or run it "
        "through pkexec or sudo."
    ),
}


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

        # Errors are checked first: a failure line must never be mistaken for
        # progress because it shares a word with a success message.
        if any(marker in lowered for marker in PRIVILEGE_ERROR_MARKERS):
            return ParsedLogLine(raw=raw, kind=ParsedLogKind.PRIVILEGE_ERROR, message=raw)

        if "gateway certificate validation failed" in lowered or "trusted-cert" in lowered:
            return ParsedLogLine(raw=raw, kind=ParsedLogKind.CERTIFICATE_ERROR, message=raw)

        if any(marker in lowered for marker in AUTHENTICATION_ERROR_MARKERS):
            return ParsedLogLine(raw=raw, kind=ParsedLogKind.AUTHENTICATION_ERROR, message=raw)

        if any(marker in lowered for marker in GATEWAY_ERROR_MARKERS):
            return ParsedLogLine(raw=raw, kind=ParsedLogKind.GATEWAY_ERROR, message=raw)

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
            ParsedLogKind.PRIVILEGE_ERROR,
            ParsedLogKind.ERROR,
        }:
            return VPNConnectionState.FAILED

        return VPNConnectionState.UNKNOWN
