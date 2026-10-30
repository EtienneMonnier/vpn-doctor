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
from vpn_doctor.i18n import N_
from vpn_doctor.models.diagnostic import DiagnosticItem, DiagnosticSeverity

# Reasons printed by `nmcli connection up` after "Connection activation failed:".
ACTIVATION_RULES = (
    LogRule(
        ("Invalid secrets",),
        N_("Credentials"),
        N_("NetworkManager reports that the VPN refused the credentials."),
        N_("Check the username and the password in the connection settings, then try again."),
    ),
    LogRule(
        ("Secrets are required to connect WireGuard VPN",),
        N_("WireGuard key"),
        N_("The WireGuard private key is missing from the connection."),
        N_("Import the configuration again, or set the private key in the connection settings."),
    ),
    LogRule(
        ("Secrets were required, but not provided", "No valid secrets"),
        N_("Password prompt"),
        N_("The VPN needed a password, but none was entered."),
        N_(
            "Enter the password when GNOME asks for it. Without a desktop session, connect "
            "with `nmcli --ask connection up <name>`."
        ),
    ),
    LogRule(
        ("The VPN service failed to start", "The VPN service did not start in time"),
        N_("VPN plugin"),
        N_("NetworkManager could not start the VPN plugin for this connection type."),
        N_(
            "Check that the matching plugin package is installed (for example "
            "NetworkManager-openvpn), then restart NetworkManager."
        ),
    ),
    LogRule(
        ("The VPN service returned invalid configuration",),
        N_("Server configuration"),
        N_("The VPN server sent settings that NetworkManager could not apply."),
        N_("Ask the VPN administrator to check the addresses and routes pushed to clients."),
    ),
    LogRule(
        ("IP configuration could not be reserved",),
        N_("IP address"),
        N_("The tunnel started but no IP address could be configured."),
        N_("The VPN server may have no free address left. Contact the VPN administrator."),
    ),
    LogRule(
        ("The connection attempt timed out", "Timeout expired"),
        N_("Timeout"),
        N_("The connection did not complete in time."),
        N_("Check that the gateway is reachable, and answer any two-factor prompt quickly."),
    ),
    LogRule(
        ("The VPN service stopped unexpectedly",),
        N_("VPN program"),
        N_("The VPN program started, then stopped. Its own log explains why."),
        N_("Look at the plugin log lines just before the failure."),
    ),
)

# Messages printed by the VPN programs that NetworkManager plugins run.
PLUGIN_RULES = (
    LogRule(
        ("AUTH_FAILED", "Could not authenticate to gateway", "Could not authenticate to the gateway"),
        N_("Credentials"),
        N_("The VPN server refused the login."),
        N_(
            "Check the username, the password and, for FortiGate, the realm. If they are "
            "correct, the account may be locked or not allowed to use the VPN."
        ),
    ),
    LogRule(
        ("private key password verification failed",),
        N_("Private key"),
        N_("The password protecting the client private key is wrong."),
        N_("Enter the private key password again in the connection settings."),
    ),
    LogRule(
        ("VERIFY ERROR", "Server certificate verify failed", "SSL certificate authentication failed",
         "Gateway certificate validation failed"),
        N_("Server certificate"),
        N_("The VPN server certificate is not trusted."),
        N_(
            "Verify the certificate with the VPN administrator, then set the right CA "
            "certificate or fingerprint in the connection settings."
        ),
    ),
    LogRule(
        ("TLS key negotiation failed", "TLS handshake failed"),
        N_("No answer from the server"),
        N_("The VPN server did not complete the secure handshake."),
        N_(
            "The port or protocol may be blocked by the local network (OpenVPN often uses "
            "UDP). Try another network, or check the port and protocol in the settings."
        ),
    ),
    LogRule(
        ("Cannot resolve host address", "getaddrinfo:"),
        N_("Server name"),
        N_("The VPN server name could not be resolved."),
        N_("Check the gateway name in the connection settings and your DNS."),
    ),
    LogRule(
        ("Failed to connect to host", "Could not connect to gateway", "Connection refused",
         "No route to host", "Network is unreachable"),
        N_("Gateway unreachable"),
        N_("The VPN gateway could not be reached."),
        N_("Check your Internet connection, the gateway address and port, and any firewall."),
    ),
    LogRule(
        ("Cookie is no longer valid",),
        N_("Session expired"),
        N_("The VPN server ended the session."),
        N_("Connect again. If it happens often, ask the administrator about session limits."),
    ),
    LogRule(
        ("Options error",),
        N_("Configuration file"),
        N_("The VPN configuration contains an option the VPN program rejects."),
        N_("Import the configuration again, or remove the reported option."),
    ),
    LogRule(
        ("Inactivity timeout",),
        N_("Connection lost"),
        N_("The VPN server stopped answering keepalive messages."),
        N_("The network may be unstable, or the server dropped the session."),
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
