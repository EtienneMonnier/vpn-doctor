import os
import stat
import time

import pytest

from vpn_doctor.backend.networkmanager import (
    NetworkManagerBackend,
    parse_gateway,
    parse_vpn_data,
    split_terse,
)
from vpn_doctor.core.controller import ApplicationController
from vpn_doctor.diagnostics.vpn_plugins import explain_failure
from vpn_doctor.models.status import VPNConnectionState

UUID_OVPN = "11111111-1111-1111-1111-111111111111"
UUID_WG = "22222222-2222-2222-2222-222222222222"

FAKE_NMCLI = f"""#!/bin/sh
case "$*" in
  "-t -f NAME,UUID,TYPE connection show")
    echo "Office\\\\: VPN:{UUID_OVPN}:vpn"
    echo "Home WG:{UUID_WG}:wireguard"
    echo "Wi-Fi:33333333-3333-3333-3333-333333333333:802-11-wireless"
    ;;
  "-g vpn.service-type connection show uuid {UUID_OVPN}")
    echo "org.freedesktop.NetworkManager.openvpn" ;;
  "-g vpn.data connection show uuid {UUID_OVPN}")
    echo "connection-type = password, remote = vpn.example.com:1194, username = demo-user" ;;
  "-t -f UUID,STATE connection show --active")
    [ -f "$STATE_FILE" ] && cat "$STATE_FILE" ;;
  "--wait 120 connection up uuid {UUID_OVPN}")
    sleep 0.3
    echo "Error: Connection activation failed: The VPN service stopped unexpectedly"
    exit 4 ;;
  "--wait 120 connection up uuid {UUID_WG}")
    echo "{UUID_WG}:activated" > "$STATE_FILE"
    echo "Connection successfully activated (D-Bus active path: /org/freedesktop/NetworkManager/ActiveConnection/7)" ;;
  "connection down uuid {UUID_WG}")
    rm -f "$STATE_FILE" ;;
esac
"""

FAKE_JOURNALCTL = """#!/bin/sh
echo '{"SYSLOG_IDENTIFIER": "NetworkManager", "MESSAGE": "<info>  [1.0] device (wlan0): DHCP lease renewed"}'
echo '{"SYSLOG_IDENTIFIER": "nm-openconnect", "MESSAGE": "Failed to connect to host other.example.com"}'
echo '{"SYSLOG_IDENTIFIER": "nm-openvpn", "MESSAGE": "OpenVPN 2.7.8 x86_64-redhat-linux-gnu"}'
echo '{"SYSLOG_IDENTIFIER": "nm-openvpn", "MESSAGE": "AUTH: Received control message: AUTH_FAILED"}'
sleep 30
"""


@pytest.fixture
def fake_networkmanager(tmp_path, monkeypatch):
    bin_dir = tmp_path / "nm-bin"
    bin_dir.mkdir()
    for name, script in (("nmcli", FAKE_NMCLI), ("journalctl", FAKE_JOURNALCTL)):
        tool = bin_dir / name
        tool.write_text(script, encoding="utf-8")
        tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("STATE_FILE", str(tmp_path / "active"))


def _wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and not predicate():
        time.sleep(0.05)


def test_split_terse_honours_escapes():
    assert split_terse("Office\\: VPN:abc:vpn") == ["Office: VPN", "abc", "vpn"]


def test_parse_vpn_data():
    data = parse_vpn_data("remote = vpn.example.com:1194, username = demo-user")
    assert data == {"remote": "vpn.example.com:1194", "username": "demo-user"}


def test_lists_vpn_and_wireguard_connections(fake_networkmanager):
    profiles = NetworkManagerBackend().list_profiles()

    assert [(p.name, p.vpn_type) for p in profiles] == [
        ("Office: VPN", "openvpn"),
        ("Home WG", "wireguard"),
    ]
    assert (profiles[0].host, profiles[0].port) == ("vpn.example.com", 1194)


def test_failure_is_explained_from_plugin_log(fake_networkmanager):
    backend = NetworkManagerBackend()
    profile = backend.list_profiles()[0]
    logs = []

    backend.connect(profile, on_log=logs.append)
    _wait_for(lambda: backend.status(profile).state == VPNConnectionState.FAILED)
    status = backend.status(profile)

    assert status.state == VPNConnectionState.FAILED
    assert "refused the login" in status.suggestion
    assert "AUTH: Received control message: AUTH_FAILED" in logs
    assert not any("wlan0" in line for line in logs)
    assert not any("other.example.com" in line for line in logs)


def test_connect_and_disconnect_follow_networkmanager(fake_networkmanager):
    backend = NetworkManagerBackend()
    profile = backend.list_profiles()[1]

    backend.connect(profile)
    _wait_for(lambda: not backend.sessions[profile.nm_uuid].runner.is_running)
    assert backend.status(profile).state == VPNConnectionState.CONNECTED

    backend.disconnect(profile)
    assert backend.status(profile).state == VPNConnectionState.DISCONNECTED


def test_status_of_another_connection_does_not_touch_current_one(fake_networkmanager):
    backend = NetworkManagerBackend()
    office, home = backend.list_profiles()

    backend.connect(home)
    _wait_for(lambda: not backend.sessions[home.nm_uuid].runner.is_running)

    assert backend.status(office).state == VPNConnectionState.DISCONNECTED
    assert backend.status(home).state == VPNConnectionState.CONNECTED
    backend.disconnect(home)


def test_explain_failure_puts_plugin_cause_first():
    items = explain_failure(
        ["Error: Connection activation failed: The VPN service stopped unexpectedly"],
        ["TLS Error: TLS key negotiation failed to occur within 60 seconds"],
    )

    assert [item.name for item in items] == ["No answer from the server", "VPN program"]


def test_controller_merges_networkmanager_and_json_profiles(fake_networkmanager, capsys):
    controller = ApplicationController()

    assert controller.run(["profiles"]) == 0
    out = capsys.readouterr().out
    assert "Office: VPN (openvpn via NetworkManager)" in out
    assert "Demo Fortinet VPN" not in out

    controller.select_profile("Home WG")
    assert controller.requires_password() is False


def test_parse_vpn_data_unescapes_nmcli_values():
    data = parse_vpn_data("gateway = https\\://vpn.example.com\\:8443/staff, protocol = anyconnect")
    assert data["gateway"] == "https://vpn.example.com:8443/staff"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("vpn.example.com", ("vpn.example.com", 0)),
        ("vpn.example.com:1194", ("vpn.example.com", 1194)),
        ("vpn.example.com 1194", ("vpn.example.com", 1194)),
        ("vpn.example.com:1194:udp", ("vpn.example.com", 1194)),
        ("https://vpn.example.com:8443/staff", ("vpn.example.com", 8443)),
        ("https://vpn.example.com", ("vpn.example.com", 0)),
    ],
)
def test_parse_gateway(value, expected):
    assert parse_gateway(value) == expected


def test_two_connections_have_independent_sessions(fake_networkmanager):
    backend = NetworkManagerBackend()
    office, home = backend.list_profiles()
    office_logs, home_logs = [], []

    backend.connect(home, on_log=home_logs.append)
    backend.connect(office, on_log=office_logs.append)
    _wait_for(lambda: backend.status(office).state == VPNConnectionState.FAILED)
    _wait_for(lambda: backend.status(home).state == VPNConnectionState.CONNECTED)

    assert backend.status(office).state == VPNConnectionState.FAILED
    assert backend.status(home).state == VPNConnectionState.CONNECTED
    assert "AUTH: Received control message: AUTH_FAILED" in office_logs
    assert not any("AUTH_FAILED" in line for line in home_logs)
    backend.disconnect()
    assert backend.status(home).state == VPNConnectionState.DISCONNECTED
