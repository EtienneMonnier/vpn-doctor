"""Remote Desktop (RDP) diagnostics.

A VPN is often only the road to a service. When "the VPN does not work", the
tunnel may be fine while the Remote Desktop server behind it refuses the
session. This module checks an RDP server step by step, without sending any
credentials, and explains FreeRDP / Remmina client errors.

Connection phases, in order:

1. TCP connection to the RDP port;
2. X.224 negotiation (the server chooses standard RDP, TLS or NLA);
3. TLS handshake;
4. NLA / CredSSP authentication          <- needs credentials, client only;
5. licensing, then session activation   <- client only.

The probe covers phases 1 to 3. Phases 4 and 5 are explained from client logs.
"""

from __future__ import annotations

import socket
import ssl
import struct
from collections.abc import Iterable
from dataclasses import dataclass

from vpn_doctor.diagnostics.log_rules import LogRule, match_rules
from vpn_doctor.i18n import N_, _
from vpn_doctor.models.diagnostic import DiagnosticItem, DiagnosticReport, DiagnosticSeverity

DEFAULT_RDP_PORT = 3389

# [MS-RDPBCGR] 2.2.1.1.1 / 2.2.1.2.1 / 2.2.1.2.2
TYPE_RDP_NEG_RSP = 0x02
TYPE_RDP_NEG_FAILURE = 0x03
PROTOCOL_SSL = 0x01
PROTOCOL_HYBRID = 0x02

SELECTED_PROTOCOLS = {
    0x00: N_("standard RDP security"),
    0x01: "TLS",
    0x02: "NLA (CredSSP)",
    0x04: "RDSTLS",
    0x08: N_("NLA (CredSSP with early user authorization)"),
    0x10: N_("RDS AAD authentication"),
}

NEGOTIATION_FAILURES = {
    0x01: N_("the server requires TLS"),
    0x02: N_("the server does not allow TLS"),
    0x03: N_("the server has no TLS certificate"),
    0x04: N_("the client request was inconsistent"),
    0x05: N_("the server requires NLA (CredSSP)"),
    0x06: N_("the server requires TLS with user authentication"),
}


@dataclass(frozen=True)
class NegotiationResult:
    """Server answer to the X.224 connection request."""

    accepted: bool
    protocol: int | None = None
    failure_code: int | None = None

    @property
    def uses_tls(self) -> bool:
        return self.accepted and self.protocol not in (None, 0x00)

    def describe(self) -> str:
        if self.accepted:
            if self.protocol in SELECTED_PROTOCOLS:
                return _(SELECTED_PROTOCOLS[self.protocol])
            return _("protocol 0x{code:x}").format(code=self.protocol)
        if self.failure_code in NEGOTIATION_FAILURES:
            return _(NEGOTIATION_FAILURES[self.failure_code])
        return _("failure code 0x{code:x}").format(code=self.failure_code)


def build_connection_request(requested_protocols: int = PROTOCOL_SSL | PROTOCOL_HYBRID) -> bytes:
    """Build a TPKT + X.224 Connection Request carrying an RDP_NEG_REQ."""
    negotiation = struct.pack("<BBHI", 0x01, 0x00, 8, requested_protocols)
    x224 = bytes([6 + len(negotiation), 0xE0, 0, 0, 0, 0, 0]) + negotiation
    return struct.pack(">BBH", 3, 0, 4 + len(x224)) + x224


def parse_negotiation_response(data: bytes) -> NegotiationResult:
    """Parse the TPKT + X.224 Connection Confirm returned by the server.

    Raises ValueError when the bytes are not an RDP answer.
    """
    if len(data) < 11 or data[0] != 3 or data[5] != 0xD0:
        raise ValueError("not an RDP X.224 connection confirm")

    if len(data) < 19:
        # Old servers answer without negotiation data: standard RDP security.
        return NegotiationResult(accepted=True, protocol=0x00)

    kind, _flags, _length, value = struct.unpack("<BBHI", data[11:19])
    if kind == TYPE_RDP_NEG_RSP:
        return NegotiationResult(accepted=True, protocol=value)
    if kind == TYPE_RDP_NEG_FAILURE:
        return NegotiationResult(accepted=False, failure_code=value)
    raise ValueError(f"unexpected negotiation type 0x{kind:x}")


def probe_rdp(host: str, port: int = DEFAULT_RDP_PORT, timeout: float = 5.0) -> DiagnosticReport:
    """Check phases 1 to 3 of an RDP connection. No credentials are sent."""
    target = f"{host}:{port}"
    summary = _("RDP diagnostics")
    items: list[DiagnosticItem] = []

    try:
        sock = socket.create_connection((host, port), timeout=timeout)
    except OSError as exc:
        items.append(
            _error(
                _("RDP port"),
                _("{target} is not reachable ({error}).").format(
                    target=target, error=exc.strerror or exc
                ),
                _(
                    "Check that the VPN routes this address, that Remote Desktop is enabled "
                    "on the server and that no firewall blocks the port."
                ),
            )
        )
        return DiagnosticReport.from_items(summary, items)

    with sock:
        items.append(
            DiagnosticItem(
                _("RDP port"), True, _("{target} accepts TCP connections.").format(target=target)
            )
        )

        try:
            sock.sendall(build_connection_request())
            negotiation = parse_negotiation_response(sock.recv(1024))
        except (OSError, ValueError) as exc:
            items.append(
                _error(
                    _("RDP negotiation"),
                    _("The service on {target} did not answer like an RDP server ({error}).").format(
                        target=target, error=exc
                    ),
                    _("Check the port number: another service may be listening on it."),
                )
            )
            return DiagnosticReport.from_items(summary, items)

        if not negotiation.accepted:
            items.append(
                _error(
                    _("RDP negotiation"),
                    _("The server refused the security negotiation: {reason}.").format(
                        reason=negotiation.describe()
                    ),
                    _(
                        "Align the security setting of the client (Remmina: Advanced > Security "
                        "protocol negotiation) with what the server requires."
                    ),
                )
            )
            return DiagnosticReport.from_items(summary, items)

        items.append(
            DiagnosticItem(
                _("RDP negotiation"),
                True,
                _("The server selected {protocol}.").format(protocol=negotiation.describe()),
            )
        )

        if negotiation.uses_tls:
            items.append(_check_tls(sock, timeout))

    items.append(
        DiagnosticItem(
            _("Beyond this probe"),
            True,
            _(
                "Authentication, licensing and session start need credentials and are not "
                "tested here. If the client still fails, analyse its log with --log."
            ),
        )
    )
    return DiagnosticReport.from_items(summary, items)


def _check_tls(sock: socket.socket, timeout: float) -> DiagnosticItem:
    # RDP servers almost always use self-signed certificates. The probe only
    # checks that a handshake is possible; trust is the client's decision.
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    sock.settimeout(timeout)
    try:
        with context.wrap_socket(sock) as tls:
            return DiagnosticItem(
                _("TLS handshake"), True, _("TLS works ({version}).").format(version=tls.version())
            )
    except (OSError, ssl.SSLError) as exc:
        return _error(
            _("TLS handshake"),
            _("The TLS handshake failed ({error}).").format(error=exc),
            _(
                "Old Windows servers only offer TLS 1.0/1.1. Lower the client TLS security "
                "level (Remmina: Advanced > TLS Security Level = 0) or update the server."
            ),
        )


# Markers verified against FreeRDP 3 (used by Remmina). Ordered from the most
# specific explanation to the most generic one.
FREERDP_LOG_RULES = (
    LogRule(
        ("license connection sequence aborted", "ERRINFO_LICENSE_NO_LICENSE"),
        N_("Remote Desktop licensing"),
        N_(
            "Your credentials were accepted, then the server closed the connection during "
            "the Remote Desktop licensing phase. This is a server-side problem, not a VPN "
            "or password problem."
        ),
        N_(
            "The RDS licensing grace period has probably expired or the license server is "
            "unreachable. To confirm, connect in console mode, which bypasses licensing "
            "(Remmina: Advanced > Attach to console, xfreerdp: /admin). The server "
            "administrator should check RD Licensing and the TerminalServices-Licensing "
            "event log."
        ),
    ),
    LogRule(
        ("ERRCONNECT_PASSWORD_EXPIRED", "ERRCONNECT_PASSWORD_CERTAINLY_EXPIRED",
         "ERRCONNECT_PASSWORD_MUST_CHANGE"),
        N_("Expired password"),
        N_("The Windows password has expired or must be changed."),
        N_(
            "NLA cannot change a password during login. Change it from another Windows "
            "session or ask the administrator to reset it."
        ),
    ),
    LogRule(
        ("ERRCONNECT_ACCOUNT_LOCKED_OUT", "ERRCONNECT_ACCOUNT_DISABLED",
         "ERRCONNECT_ACCOUNT_EXPIRED", "ERRCONNECT_ACCOUNT_RESTRICTION"),
        N_("Windows account"),
        N_("The Windows account is locked, disabled, expired or restricted."),
        N_(
            "Ask the server administrator to check the account in Active Directory or in "
            "the local users of the server."
        ),
    ),
    LogRule(
        ("ERRCONNECT_LOGON_FAILURE", "ERRCONNECT_AUTHENTICATION_FAILED"),
        N_("Credentials"),
        N_("The server rejected the username or the password."),
        N_(
            "Check the password, the username and the domain. A domain account is often "
            "written DOMAIN\\user."
        ),
    ),
    LogRule(
        ("ERRCONNECT_LOGON_TYPE_NOT_GRANTED", "ERRINFO_SERVER_INSUFFICIENT_PRIVILEGES",
         "ERRCONNECT_INSUFFICIENT_PRIVILEGES", "ERRINFO_SERVER_DENIED_CONNECTION"),
        N_("Remote Desktop permission"),
        N_("The account is valid but not allowed to open a Remote Desktop session."),
        N_("Ask the administrator to add the account to the Remote Desktop Users group."),
    ),
    LogRule(
        ("ERRCONNECT_TLS_CONNECT_FAILED",),
        N_("TLS"),
        N_("The client could not establish TLS with the server."),
        N_(
            "Lower the client TLS security level (Remmina: Advanced > TLS Security Level = 0) "
            "for old servers."
        ),
    ),
    LogRule(
        ("ERRCONNECT_DNS_NAME_NOT_FOUND",),
        N_("Server name"),
        N_("The client could not resolve the server name."),
        N_("Check the name, or the DNS servers pushed by the VPN."),
    ),
    LogRule(
        ("ERRCONNECT_CONNECT_FAILED", "ERRINFO_CONNECT_FAILED"),
        N_("Network"),
        N_("The client could not reach the server."),
        N_("Run `vpn-doctor rdp HOST` to test the route, the port and the negotiation."),
    ),
    LogRule(
        ("Configuration file does not specify default realm",),
        N_("Kerberos warnings"),
        N_(
            "FreeRDP tried Kerberos first, found no realm and fell back to NTLM. These "
            "errors are harmless."
        ),
        None,
        DiagnosticSeverity.INFO,
    ),
)


def analyze_freerdp_log(lines: Iterable[str]) -> list[DiagnosticItem]:
    """Explain known FreeRDP / Remmina errors found in log lines.

    Raw lines are never copied into the result: they contain host names,
    usernames and domains.
    """
    matched = match_rules(lines, FREERDP_LOG_RULES)
    if not matched:
        return [DiagnosticItem(_("Client log"), True, _("No known FreeRDP error was found."))]
    return [rule.to_item() for rule in matched]


def _error(name: str, message: str, suggestion: str) -> DiagnosticItem:
    return DiagnosticItem(name, False, message, suggestion, DiagnosticSeverity.ERROR)
