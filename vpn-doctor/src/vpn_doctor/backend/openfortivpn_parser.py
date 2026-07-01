"""OpenFortiVPN log parsing."""

from __future__ import annotations

from dataclasses import dataclass

from vpn_doctor.models.status import VPNConnectionState


@dataclass(frozen=True)
class ParsedOpenFortiVPNLine:
    """Normalized information extracted from an openfortivpn log line."""

    line: str
    state: VPNConnectionState | None = None
    error_code: str | None = None


class OpenFortiVPNLogParser:
    """Parse openfortivpn logs into normalized states and error codes."""

    def parse(self, line: str) -> ParsedOpenFortiVPNLine:
        normalized = line.lower()

        if "connected to gateway" in normalized:
            return ParsedOpenFortiVPNLine(line=line, state=VPNConnectionState.CONNECTING)
        if "authenticated" in normalized:
            return ParsedOpenFortiVPNLine(line=line, state=VPNConnectionState.AUTHENTICATING)
        if "remote gateway has allocated a vpn" in normalized:
            return ParsedOpenFortiVPNLine(line=line, state=VPNConnectionState.CONFIGURING)
        if "negotiation complete" in normalized:
            return ParsedOpenFortiVPNLine(line=line, state=VPNConnectionState.CONFIGURING)
        if "interface ppp" in normalized and "is up" in normalized:
            return ParsedOpenFortiVPNLine(line=line, state=VPNConnectionState.CONFIGURING)
        if "tunnel is up and running" in normalized:
            return ParsedOpenFortiVPNLine(line=line, state=VPNConnectionState.CONNECTED)
        if "connection terminated" in normalized or "logged out" in normalized:
            return ParsedOpenFortiVPNLine(line=line, state=VPNConnectionState.DISCONNECTED)
        if "gateway certificate validation failed" in normalized:
            return ParsedOpenFortiVPNLine(
                line=line,
                state=VPNConnectionState.FAILED,
                error_code="certificate-validation-failed",
            )
        if "could not authenticate" in normalized or "authentication failed" in normalized:
            return ParsedOpenFortiVPNLine(
                line=line,
                state=VPNConnectionState.FAILED,
                error_code="authentication-failed",
            )
        if "connect timer expired" in normalized or "timed out" in normalized:
            return ParsedOpenFortiVPNLine(
                line=line,
                state=VPNConnectionState.FAILED,
                error_code="timeout",
            )
        if normalized.startswith("error:"):
            return ParsedOpenFortiVPNLine(line=line, state=VPNConnectionState.FAILED)

        return ParsedOpenFortiVPNLine(line=line)

    def parse_state(self, line: str) -> VPNConnectionState | None:
        """Backward-compatible helper used by existing tests."""
        return self.parse(line).state
