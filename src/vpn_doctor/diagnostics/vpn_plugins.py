"""Explain NetworkManager VPN activation failures.

GNOME usually reports a failed VPN as "activation failed" and nothing more.
The real cause is split between the reason given by NetworkManager and the
log of the VPN plugin (openvpn, openconnect, openfortivpn...) in the journal.
These rules turn both into one readable explanation.

Every marker was checked against NetworkManager 1.56, OpenVPN 2.7,
OpenConnect 9 and openfortivpn 1.23.
"""

from __future__ import annotations

from collections.abc import Iterable

from vpn_doctor.diagnostics.log_rules import LogRule, match_rules
from vpn_doctor.models.diagnostic import DiagnosticItem, DiagnosticSeverity

# Reasons printed by `nmcli connection up` after "Connection activation failed:".
ACTIVATION_RULES = (
    LogRule(
        ("Invalid secrets",),
        "Credentials",
        "NetworkManager reports that the VPN refused the credentials.",
        "Check the username and the password in the connection settings, then try again.",
    ),
    LogRule(
        ("Secrets are required to connect WireGuard VPN",),
        "WireGuard key",
        "The WireGuard private key is missing from the connection.",
        "Import the configuration again, or set the private key in the connection settings.",
    ),
    LogRule(
        ("Secrets were required, but not provided", "No valid secrets"),
        "Password prompt",
        "The VPN needed a password, but none was entered.",
        "Enter the password when GNOME asks for it. Without a desktop session, connect "
        "with `nmcli --ask connection up <name>`.",
    ),
    LogRule(
        ("The VPN service failed to start", "The VPN service did not start in time"),
        "VPN plugin",
        "NetworkManager could not start the VPN plugin for this connection type.",
        "Check that the matching plugin package is installed (for example "
        "NetworkManager-openvpn), then restart NetworkManager.",
    ),
    LogRule(
        ("The VPN service returned invalid configuration",),
        "Server configuration",
        "The VPN server sent settings that NetworkManager could not apply.",
        "Ask the VPN administrator to check the addresses and routes pushed to clients.",
    ),
    LogRule(
        ("IP configuration could not be reserved",),
        "IP address",
        "The tunnel started but no IP address could be configured.",
        "The VPN server may have no free address left. Contact the VPN administrator.",
    ),
    LogRule(
        ("The connection attempt timed out", "Timeout expired"),
        "Timeout",
        "The connection did not complete in time.",
        "Check that the gateway is reachable, and answer any two-factor prompt quickly.",
    ),
    LogRule(
        ("The VPN service stopped unexpectedly",),
        "VPN program",
        "The VPN program started, then stopped. Its own log explains why.",
        "Look at the plugin log lines just before the failure.",
    ),
)

# Messages printed by the VPN programs that NetworkManager plugins run.
PLUGIN_RULES = (
    LogRule(
        ("AUTH_FAILED", "Could not authenticate to gateway", "Could not authenticate to the gateway"),
        "Credentials",
        "The VPN server refused the login.",
        "Check the username, the password and, for FortiGate, the realm. If they are "
        "correct, the account may be locked or not allowed to use the VPN.",
    ),
    LogRule(
        ("private key password verification failed",),
        "Private key",
        "The password protecting the client private key is wrong.",
        "Enter the private key password again in the connection settings.",
    ),
    LogRule(
        ("VERIFY ERROR", "Server certificate verify failed", "SSL certificate authentication failed",
         "Gateway certificate validation failed"),
        "Server certificate",
        "The VPN server certificate is not trusted.",
        "Verify the certificate with the VPN administrator, then set the right CA "
        "certificate or fingerprint in the connection settings.",
    ),
    LogRule(
        ("TLS key negotiation failed", "TLS handshake failed"),
        "No answer from the server",
        "The VPN server did not complete the secure handshake.",
        "The port or protocol may be blocked by the local network (OpenVPN often uses "
        "UDP). Try another network, or check the port and protocol in the settings.",
    ),
    LogRule(
        ("Cannot resolve host address", "getaddrinfo:"),
        "Server name",
        "The VPN server name could not be resolved.",
        "Check the gateway name in the connection settings and your DNS.",
    ),
    LogRule(
        ("Failed to connect to host", "Could not connect to gateway", "Connection refused",
         "No route to host", "Network is unreachable"),
        "Gateway unreachable",
        "The VPN gateway could not be reached.",
        "Check your Internet connection, the gateway address and port, and any firewall.",
    ),
    LogRule(
        ("Cookie is no longer valid",),
        "Session expired",
        "The VPN server ended the session.",
        "Connect again. If it happens often, ask the administrator about session limits.",
    ),
    LogRule(
        ("Options error",),
        "Configuration file",
        "The VPN configuration contains an option the VPN program rejects.",
        "Import the configuration again, or remove the reported option.",
    ),
    LogRule(
        ("Inactivity timeout",),
        "Connection lost",
        "The VPN server stopped answering keepalive messages.",
        "The network may be unstable, or the server dropped the session.",
        DiagnosticSeverity.WARNING,
    ),
)


def explain_failure(
    activation_lines: Iterable[str],
    plugin_lines: Iterable[str],
) -> list[DiagnosticItem]:
    """Explain a failed activation, the most precise cause first.

    The plugin log usually holds the real cause, so its explanations come before
    the generic NetworkManager reason.
    """
    plugin = match_rules(plugin_lines, PLUGIN_RULES)
    activation = match_rules(activation_lines, ACTIVATION_RULES)
    return [rule.to_item() for rule in [*plugin, *activation]]
