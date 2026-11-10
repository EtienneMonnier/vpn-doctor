"""Explain NetworkManager VPN activation failures.

GNOME usually reports a failed VPN as "activation failed" and nothing more.
The real cause is split between the reason given by NetworkManager and the
log of the VPN plugin (openvpn, openconnect, openfortivpn...) in the journal.
These rules turn both into one readable explanation.

Every marker was checked against NetworkManager 1.56, OpenVPN 2.7,
OpenConnect 9, openfortivpn 1.23 and the OpenSSL 3 error strings (OpenVPN
prints them as "OpenSSL: error:...:<reason>").
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
    # Specific certificate and OpenVPN causes come before the generic rules
    # below, which often match the same lines.
    LogRule(
        ("ca md too weak", "CA signature digest algorithm too weak", "ee key too small",
         "ca key too small", "EE certificate key too weak", "CA certificate key too weak"),
        N_("Weak certificate"),
        N_(
            "A certificate of this VPN uses a key or a signature that the system's "
            "cryptographic policy refuses (RSA shorter than 2048 bits, SHA-1 or MD5)."
        ),
        N_(
            "Ask the VPN administrator for new certificates (RSA 2048 bits or more, SHA-256). "
            "As a temporary workaround on Fedora or RHEL, an administrator can relax the "
            "policy, e.g. `update-crypto-policies --set DEFAULT:SHA1`; this weakens the "
            "whole system."
        ),
    ),
    LogRule(
        ("certificate has expired", "certificate is not yet valid"),
        N_("Certificate dates"),
        N_(
            "A certificate of this VPN (the server's, its authority's or yours) has expired "
            "or is not valid yet, or the clock of this computer is wrong."
        ),
        N_(
            "Check the date and time of this computer. If they are right, ask the VPN "
            "administrator to renew the certificate."
        ),
    ),
    LogRule(
        ("Decoding PKCS12 failed", "digital envelope routines::unsupported"),
        N_("Certificate file"),
        N_(
            "The PKCS#12 (.p12) file could not be opened: either its password is wrong, or "
            "it uses an old encryption (RC2, 3DES) that OpenSSL 3 no longer reads."
        ),
        N_(
            "Check its password. If it is right, re-encrypt the file: `openssl pkcs12 "
            "-legacy -in old.p12 -out tmp.pem`, then `openssl pkcs12 -export -in tmp.pem "
            "-out new.p12`, and delete tmp.pem."
        ),
    ),
    LogRule(
        ("unsupported protocol", "no protocols available"),
        N_("TLS version"),
        N_(
            "The VPN server and this computer have no TLS version in common: the server "
            "probably only offers TLS 1.0 or 1.1, which the system refuses."
        ),
        N_(
            "Ask the VPN administrator to enable TLS 1.2 or newer. Also check the minimum "
            "TLS version in the advanced settings of the connection."
        ),
    ),
    LogRule(
        ("tls-crypt unwrapping failed", "tls-crypt unwrap error",
         "incoming packet authentication failed", "packet authentication failed"),
        N_("TLS key"),
        N_(
            "The packets of the VPN server fail the extra TLS key check (tls-auth or "
            "tls-crypt): this computer and the server do not use the same key, or the same "
            "key direction."
        ),
        N_(
            "Import the configuration file from the VPN administrator again, or check the "
            "TLS authentication key and its direction (0 or 1) in the advanced settings of "
            "the connection."
        ),
    ),
    LogRule(
        ("failed to negotiate cipher", "No usable data channel cipher"),
        N_("Data cipher"),
        N_(
            "This computer and the VPN server have no data encryption algorithm in common. "
            "Recent OpenVPN versions no longer accept old ciphers such as BF-CBC."
        ),
        N_(
            "Ask the VPN administrator to enable a modern cipher such as AES-256-GCM on the "
            "server. Until then, the server's cipher can be added to the data ciphers in "
            "the advanced settings of the connection, if your security policy allows it."
        ),
    ),
    LogRule(
        ("server pushed compression settings that are not allowed",
         "Compression is not allowed since allow-compression"),
        N_("Compression"),
        N_(
            "The VPN server asks for compression, which recent OpenVPN versions refuse "
            "because compressing encrypted traffic can leak its content (VORACLE)."
        ),
        N_(
            "Ask the VPN administrator to disable compression on the server (comp-lzo, "
            "compress). Allowing it on this computer is a security risk."
        ),
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
