import json
import shutil
import subprocess
from datetime import UTC, datetime, timedelta

import pytest

from vpn_doctor.core.controller import ApplicationController
from vpn_doctor.diagnostics.ovpn_check import (
    CertificateInfo,
    OvpnChecker,
    inspect_certificate,
    parse_ovpn,
)
from vpn_doctor.models.diagnostic import DiagnosticSeverity

NOW = datetime(2026, 11, 10, tzinfo=UTC)
GOOD = """client
dev tun
proto udp
remote vpn.example.com 1194
remote-cert-tls server
data-ciphers AES-256-GCM:AES-128-GCM
<ca>
-----BEGIN CERTIFICATE-----
MIIBfake
-----END CERTIFICATE-----
</ca>
"""


def certificate(**changes):
    values = dict(
        subject="CN=Example CA",
        key_type="rsa",
        key_bits=2048,
        signature="sha256WithRSAEncryption",
        not_before=NOW - timedelta(days=365),
        not_after=NOW + timedelta(days=365),
        self_signed=True,
    )
    values.update(changes)
    return CertificateInfo(**values)


def check(tmp_path, text, info=None):
    path = tmp_path / "client.ovpn"
    path.write_text(text, encoding="utf-8")
    checker = OvpnChecker(inspect=lambda pem: info or certificate(), now=lambda: NOW)
    return checker.check_file(path)


def names(items, severity=None):
    return [item.name for item in items if severity is None or item.severity == severity]


def test_parse_options_comments_and_inline_blocks():
    config = parse_ovpn(
        '# comment\n; other comment\n--remote vpn.example.com 1194 udp\n'
        'verify-x509-name "CN=vpn example" subject\n<tls-crypt>\nkey\n</tls-crypt>\n'
    )

    assert [option.name for option in config.options] == ["remote", "verify-x509-name"]
    assert config.get("verify-x509-name").args == ("CN=vpn example", "subject")
    assert config.inline["tls-crypt"] == "key"


def test_clean_file_is_ready_to_import(tmp_path):
    items = check(tmp_path, GOOD)

    assert names(items) == ["Import"]
    assert items[0].success


def test_legacy_file_is_explained(tmp_path):
    text = GOOD.replace("data-ciphers AES-256-GCM:AES-128-GCM", "cipher BF-CBC") + (
        "comp-lzo\ntls-remote vpn.example.com\nredirect-gateway def1\n"
        "dhcp-option DNS 192.0.2.53\nresolv-retry infinite\nfoo-unknown 1\n"
    )

    items = check(tmp_path, text)

    assert names(items, DiagnosticSeverity.ERROR) == ["Removed option", "Data cipher"]
    assert names(items, DiagnosticSeverity.WARNING) == [
        "Compression",
        "Ignored by NetworkManager",
        "Ignored by NetworkManager",
    ]
    note = next(item for item in items if item.severity == DiagnosticSeverity.INFO)
    assert "foo-unknown" in note.message
    assert "resolv-retry" not in note.message


@pytest.mark.parametrize(
    ("line", "severity"),
    [
        ("cipher BF-CBC", DiagnosticSeverity.ERROR),
        ("data-ciphers AES-256-GCM:DES-CBC", DiagnosticSeverity.ERROR),
        ("cipher DES-EDE3-CBC", DiagnosticSeverity.WARNING),
        ("cipher AES-256-CBC", None),
    ],
)
def test_ciphers(tmp_path, line, severity):
    items = check(tmp_path, GOOD.replace("data-ciphers AES-256-GCM:AES-128-GCM", line))

    found = [item.severity for item in items if item.name == "Data cipher"]
    assert found == ([severity] if severity else [])


@pytest.mark.parametrize(
    ("line", "warned"),
    [("comp-lzo", True), ("comp-lzo yes", True), ("comp-lzo no", False),
     ("compress lz4-v2", True), ("compress stub-v2", False), ("compress", False)],
)
def test_compression(tmp_path, line, warned):
    items = check(tmp_path, GOOD + line + "\n")

    assert ("Compression" in names(items)) is warned


def test_missing_file_is_reported_without_its_directory(tmp_path):
    items = check(tmp_path, GOOD.replace("<ca>", "ca /secret/dir/ca.crt\n<ignored>"))

    missing = [item for item in items if item.name == "Missing file"]
    assert len(missing) == 1
    assert "ca.crt" in missing[0].message
    assert "/secret/dir" not in missing[0].message


def test_relative_files_are_found_next_to_the_configuration(tmp_path):
    (tmp_path / "ta.key").write_text("key", encoding="utf-8")

    items = check(tmp_path, GOOD + "tls-auth ta.key 1\n")

    assert "Missing file" not in names(items)
    assert "TLS key" not in names(items)


def test_tls_auth_without_direction(tmp_path):
    items = check(tmp_path, GOOD + "<tls-auth>\nkey\n</tls-auth>\n")

    assert "TLS key" in names(items, DiagnosticSeverity.WARNING)
    fixed = check(tmp_path, GOOD + "key-direction 1\n<tls-auth>\nk\n</tls-auth>\n")
    assert "TLS key" not in names(fixed)


def test_server_identity_must_be_checked(tmp_path):
    items = check(tmp_path, GOOD.replace("remote-cert-tls server\n", ""))

    assert "Server identity" in names(items, DiagnosticSeverity.WARNING)


def test_inline_password_is_flagged_and_never_echoed(tmp_path):
    block = "<auth-user-pass>\ndemo-user\nnot-a-real-password\n</auth-user-pass>\n"
    items = check(tmp_path, GOOD + block)

    assert "Password in the file" in names(items, DiagnosticSeverity.WARNING)
    for item in items:
        assert "not-a-real-password" not in f"{item.message} {item.suggestion}"


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        (dict(not_after=NOW - timedelta(days=1)), "Expired certificate"),
        (dict(not_before=NOW + timedelta(days=1)), "Certificate not valid yet"),
        (dict(not_after=NOW + timedelta(days=10)), "Certificate expires soon"),
        (dict(key_bits=1024), "Weak certificate"),
        (dict(signature="sha1WithRSAEncryption", self_signed=False), "Weak certificate"),
    ],
)
def test_certificate_problems(tmp_path, changes, expected):
    items = check(tmp_path, GOOD, certificate(**changes))

    assert expected in names(items)


def test_self_signed_root_signature_is_not_checked(tmp_path):
    items = check(tmp_path, GOOD, certificate(signature="sha1WithRSAEncryption"))

    assert names(items) == ["Import"]


def test_ec_keys_are_not_too_small(tmp_path):
    items = check(tmp_path, GOOD, certificate(key_type="ec", key_bits=256))

    assert names(items) == ["Import"]


@pytest.mark.skipif(shutil.which("openssl") is None, reason="needs the openssl command")
def test_inspect_real_certificate(tmp_path):
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2",
         "-subj", "/CN=Example CA", "-keyout", str(tmp_path / "k.pem"),
         "-out", str(tmp_path / "c.pem")],
        check=True, capture_output=True,
    )

    info = inspect_certificate((tmp_path / "c.pem").read_text())

    assert info is not None
    assert (info.key_type, info.key_bits, info.self_signed) == ("rsa", 2048, True)
    assert info.signature.lower().startswith("sha256")
    assert info.subject == "CN=Example CA"
    assert info.not_after > datetime.now(UTC)


def test_inspect_garbage_returns_none():
    garbage = "-----BEGIN CERTIFICATE-----\nnope\n-----END CERTIFICATE-----"
    assert inspect_certificate(garbage) is None


def test_cli_json_and_exit_codes(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(
        "vpn_doctor.diagnostics.ovpn_check.inspect_certificate", lambda pem: None
    )
    path = tmp_path / "legacy.ovpn"
    path.write_text(GOOD + "cipher BF-CBC\n", encoding="utf-8")

    assert ApplicationController().run(["--json", "check-ovpn", str(path)]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["file"] == str(path)
    assert "Data cipher" in [item["name"] for item in data["report"]["items"]]

    path.write_text(GOOD, encoding="utf-8")
    assert ApplicationController().run(["check-ovpn", str(path)]) == 0
    assert "nmcli connection import type openvpn file" in capsys.readouterr().out


def test_cli_unreadable_file(tmp_path, capsys):
    assert ApplicationController().run(["--json", "check-ovpn", str(tmp_path / "none.ovpn")]) == 2
    assert "error" in json.loads(capsys.readouterr().out)


def test_expired_ca_next_to_a_valid_one_is_harmless(tmp_path):
    new_ca = "-----BEGIN CERTIFICATE-----\nMIIBnew\n-----END CERTIFICATE-----\n"
    two = GOOD.replace("</ca>", new_ca + "</ca>")
    old = certificate(not_after=NOW - timedelta(days=900))
    checker = OvpnChecker(
        inspect=lambda pem: old if "MIIBfake" in pem else certificate(), now=lambda: NOW
    )
    path = tmp_path / "bundle.ovpn"
    path.write_text(two, encoding="utf-8")

    items = checker.check_file(path)

    assert names(items) == ["Import", "Old certificates"]


def test_expired_only_ca_is_an_error(tmp_path):
    items = check(tmp_path, GOOD, certificate(not_after=NOW - timedelta(days=1)))

    assert "Expired certificate" in names(items, DiagnosticSeverity.ERROR)


def test_absolute_path_to_a_file_next_to_the_configuration(tmp_path):
    (tmp_path / "ca.crt").write_text("x", encoding="utf-8")

    items = check(tmp_path, GOOD.replace("<ca>", "ca /etc/openvpn/demo/ca.crt\n<ignored>"))

    missing = next(item for item in items if item.name == "Missing file")
    assert "replace the path with just `ca.crt`" in missing.suggestion


def test_damaged_files(tmp_path):
    text = GOOD + "<<<<<<< HEAD\nremote vpn.example.com 443\n=======\n</tls-crypt>\nother.ovpn\n"

    items = check(tmp_path, text)

    damaged = next(item for item in items if item.name == "Damaged file")
    assert damaged.severity == DiagnosticSeverity.WARNING
    first = GOOD.count("\n") + 1  # line of "<<<<<<< HEAD"
    assert f"{first}, {first + 2}, {first + 3}, {first + 4}" in damaged.message


def test_unclosed_inline_block(tmp_path):
    items = check(tmp_path, GOOD + "<tls-crypt>\nkey\n")

    assert "Damaged file" in names(items, DiagnosticSeverity.ERROR)


def test_old_option_names(tmp_path):
    items = check(tmp_path, GOOD + "ncp-ciphers AES-256-GCM\nroute-ipv6 2001:db8::/32\n")

    messages = " ".join(item.message for item in items)
    assert "`ncp-ciphers`" in messages and "`route-ipv6`" in messages
