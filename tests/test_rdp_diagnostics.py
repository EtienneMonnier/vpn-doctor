import socket
import threading

import pytest

from vpn_doctor.core.controller import ApplicationController
from vpn_doctor.diagnostics.rdp import (
    analyze_freerdp_log,
    build_connection_request,
    parse_negotiation_response,
    probe_rdp,
)

# Server answer captured from a Windows server that requires NLA.
NLA_RESPONSE = bytes.fromhex("030000130ed00000123400021f080002000000")
HYBRID_REQUIRED_RESPONSE = bytes.fromhex("030000130ed000001234000300080005000000")

LICENSING_LOG = """\
[WARN][com.freerdp.crypto] - [verify_cb]: Certificate verification failure 'self-signed certificate (18)'
[ERROR][com.winpr.sspi.Kerberos] - [kerberos_AcquireCredentialsHandleA]: krb5_parse_name (Configuration file does not specify default realm [-1765328160])
[ERROR][com.freerdp.api] - [rdp_client_connect_license]: license connection sequence aborted.
[ERROR][com.freerdp.core.rdp] - [rdp_recv_callback_int]: CONNECTION_STATE_LICENSING status STATE_RUN_FAILED [-1]
[ERROR][com.freerdp.core] - [rdp_client_wait_for_activation]: ERRCONNECT_CONNECT_TRANSPORT_FAILED [0x0002000D]
""".splitlines()


def test_connection_request_asks_tls_and_nla():
    request = build_connection_request()

    assert request[:2] == b"\x03\x00"
    assert len(request) == int.from_bytes(request[2:4], "big")
    assert request[-4:] == b"\x03\x00\x00\x00"


def test_parse_negotiation_selects_nla():
    result = parse_negotiation_response(NLA_RESPONSE)

    assert result.accepted
    assert result.describe() == "NLA (CredSSP)"
    assert result.uses_tls


def test_parse_negotiation_failure():
    result = parse_negotiation_response(HYBRID_REQUIRED_RESPONSE)

    assert not result.accepted
    assert result.describe() == "the server requires NLA (CredSSP)"


def test_parse_negotiation_rejects_non_rdp_data():
    with pytest.raises(ValueError):
        parse_negotiation_response(b"HTTP/1.1 400 Bad Request\r\n")


def _fake_rdp_server(response: bytes) -> int:
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)

    def serve():
        conn, _ = server.accept()
        with conn:
            conn.recv(1024)
            conn.sendall(response)
        server.close()

    threading.Thread(target=serve, daemon=True).start()
    return server.getsockname()[1]


def test_probe_reports_negotiation_and_tls_failure():
    port = _fake_rdp_server(NLA_RESPONSE)

    report = probe_rdp("127.0.0.1", port, timeout=2.0)
    items = {item.name: item for item in report.items}

    assert items["RDP port"].success
    assert items["RDP negotiation"].success
    assert "NLA" in items["RDP negotiation"].message
    assert not items["TLS handshake"].success
    assert items["TLS handshake"].suggestion


def test_probe_reports_closed_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    report = probe_rdp("127.0.0.1", port, timeout=1.0)

    assert not report.success
    assert report.items[0].name == "RDP port"
    assert "VPN routes" in report.items[0].suggestion


def test_log_analysis_explains_licensing_failure():
    items = analyze_freerdp_log(LICENSING_LOG)

    assert [item.name for item in items] == ["Remote Desktop licensing", "Kerberos warnings"]
    assert not items[0].success
    assert "Attach to console" in items[0].suggestion
    assert items[1].success


def test_log_analysis_never_copies_raw_lines():
    lines = ["[ERROR] connecting to rds.example.com as EXAMPLE\\demo-user: ERRCONNECT_LOGON_FAILURE"]

    items = analyze_freerdp_log(lines)
    text = " ".join(f"{item.message} {item.suggestion}" for item in items)

    assert items[0].name == "Credentials"
    assert "demo-user" not in text
    assert "rds.example.com" not in text


def test_log_analysis_prefers_specific_cause():
    lines = ["ERRCONNECT_CONNECT_FAILED", "ERRCONNECT_PASSWORD_EXPIRED"]

    items = analyze_freerdp_log(lines)

    assert [item.name for item in items] == ["Expired password", "Network"]


def test_log_analysis_without_known_error():
    items = analyze_freerdp_log(["INFO session started"])

    assert len(items) == 1
    assert items[0].success


def test_rdp_command_with_log_file(tmp_path, capsys):
    port = _fake_rdp_server(NLA_RESPONSE)
    log = tmp_path / "remmina.log"
    log.write_text("\n".join(LICENSING_LOG), encoding="utf-8")

    result = ApplicationController().run(["rdp", "127.0.0.1", "--port", str(port), "--log", str(log)])
    out = capsys.readouterr().out

    assert result == 1
    assert "RDP client log analysis" in out
    assert "[FAIL] Remote Desktop licensing" in out
