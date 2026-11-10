"""OpenVPN and OpenSSL messages explained by the NetworkManager plugin rules.

Lines are shaped like the journal of nm-openvpn, with placeholder addresses.
"""

import pytest

from vpn_doctor.diagnostics.vpn_plugins import PLUGIN_RULES, explain_failure

NM = "nm-openvpn[4242]: "


@pytest.mark.parametrize(
    ("line", "name"),
    [
        (
            "VERIFY ERROR: depth=0, error=CA signature digest algorithm too weak: "
            "CN=vpn.example.com, serial=1",
            "Weak certificate",
        ),
        (
            "OpenSSL: error:0A00018E:SSL routines::ca md too weak",
            "Weak certificate",
        ),
        (
            "OpenSSL: error:0A00018F:SSL routines::ee key too small",
            "Weak certificate",
        ),
        (
            "VERIFY ERROR: depth=0, error=certificate has expired: CN=vpn.example.com",
            "Certificate dates",
        ),
        (
            "VERIFY ERROR: depth=1, error=certificate is not yet valid: CN=Example CA",
            "Certificate dates",
        ),
        (
            "Decoding PKCS12 failed. Probably wrong password or unsupported/legacy encryption",
            "Certificate file",
        ),
        (
            "OpenSSL: error:0308010C:digital envelope routines::unsupported",
            "Certificate file",
        ),
        (
            "OpenSSL: error:0A000102:SSL routines::unsupported protocol",
            "TLS version",
        ),
        (
            "TLS Error: tls-crypt unwrapping failed from [AF_INET]192.0.2.10:1194",
            "TLS key",
        ),
        (
            "TLS Error: incoming packet authentication failed from [AF_INET]192.0.2.10:1194",
            "TLS key",
        ),
        (
            "OPTIONS ERROR: failed to negotiate cipher with server.  Add the server's cipher "
            "('BF-CBC') to --data-ciphers (currently 'AES-256-GCM:AES-128-GCM'), e.g."
            "--data-ciphers AES-256-GCM:AES-128-GCM:BF-CBC if you want to connect to this server.",
            "Data cipher",
        ),
        (
            "ERROR: failed to negotiate cipher with peer and --data-ciphers-fallback not "
            "enabled. No usable data channel cipher",
            "Data cipher",
        ),
        (
            "OPTIONS ERROR: server pushed compression settings that are not allowed and will "
            "result in a non-working connection. See also allow-compression in the manual.",
            "Compression",
        ),
    ],
)
def test_openvpn_messages_are_explained(line, name):
    items = explain_failure([], [NM + line])

    assert items, line
    assert items[0].name == name


def test_specific_certificate_cause_comes_before_generic_one():
    items = explain_failure(
        ["Error: Connection activation failed: The VPN service stopped unexpectedly"],
        [NM + "VERIFY ERROR: depth=0, error=certificate has expired: CN=vpn.example.com"],
    )

    assert [item.name for item in items] == [
        "Certificate dates",
        "Server certificate",
        "VPN program",
    ]


def test_tls_key_mismatch_comes_before_handshake_timeout():
    items = explain_failure(
        [],
        [
            NM + "TLS Error: tls-crypt unwrapping failed from [AF_INET]192.0.2.10:1194",
            NM + "TLS Error: TLS key negotiation failed to occur within 60 seconds",
        ],
    )

    assert [item.name for item in items] == ["TLS key", "No answer from the server"]


def test_raw_log_lines_never_reach_the_explanation():
    line = NM + "TLS Error: tls-crypt unwrapping failed from [AF_INET]192.0.2.10:1194"

    for item in explain_failure([], [line]):
        assert "192.0.2.10" not in f"{item.message} {item.suggestion}"


def test_every_rule_has_markers_and_texts():
    for rule in PLUGIN_RULES:
        assert rule.markers and all(rule.markers)
        assert rule.name and rule.message and rule.suggestion
