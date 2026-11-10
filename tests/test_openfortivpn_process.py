from vpn_doctor.backend.openfortivpn_process import OpenFortiVPNProcess
from vpn_doctor.models.profile import VPNProfile


def test_openfortivpn_command_does_not_include_password():
    profile = VPNProfile(
        name="Demo",
        backend="openfortivpn",
        host="vpn.example.com",
        port=443,
        username="demo",
        trusted_cert="abc123",
        realm="DEMO",
    )

    command = OpenFortiVPNProcess().build_command(profile)

    assert command == [
        "openfortivpn",
        "vpn.example.com:443",
        "-c",
        "/dev/null",
        "-u",
        "demo",
        "--trusted-cert",
        "abc123",
        "--realm",
        "DEMO",
    ]
    assert "password" not in " ".join(command).lower()


def test_openfortivpn_connect_dry_run_returns_command():
    profile = VPNProfile(
        name="Demo",
        backend="openfortivpn",
        host="vpn.example.com",
        port=443,
        username="demo",
    )

    command = OpenFortiVPNProcess().connect(profile, dry_run=True)

    assert command == ["openfortivpn", "vpn.example.com:443", "-c", "/dev/null", "-u", "demo"]


def test_openfortivpn_connect_dry_run_includes_privilege_command():
    profile = VPNProfile(
        name="Demo",
        backend="openfortivpn",
        host="vpn.example.com",
        port=443,
    )

    command = OpenFortiVPNProcess(privilege_command=("pkexec",)).connect(profile, dry_run=True)

    assert command[:2] == ["pkexec", "openfortivpn"]


def test_openfortivpn_command_passes_client_certificate_paths():
    profile = VPNProfile(
        name="Demo",
        backend="openfortivpn",
        host="vpn.example.com",
        port=443,
        user_cert="/etc/openfortivpn/demo-cert.pem",
        user_key="/etc/openfortivpn/demo-key.pem",
    )

    command = OpenFortiVPNProcess().build_command(profile)

    assert command[-4:] == [
        "--user-cert",
        "/etc/openfortivpn/demo-cert.pem",
        "--user-key",
        "/etc/openfortivpn/demo-key.pem",
    ]


FAKE_HELPER = """#!/bin/sh
read request
echo "REQUEST $request"
read password
echo "INFO:   Tunnel is up and running."
while read line; do :; done
echo "stdin closed, stopping"
"""


def test_helper_mode_sends_profile_then_password_and_stops_on_stdin_close(tmp_path):
    import json
    import time

    from vpn_doctor.models.status import VPNConnectionState

    fake = tmp_path / "vpn-doctor-helper"
    fake.write_text(FAKE_HELPER, encoding="utf-8")
    fake.chmod(0o755)
    profile = VPNProfile(
        name="Demo",
        backend="openfortivpn",
        host="vpn.example.com",
        port=443,
        username="demo",
    )
    process = OpenFortiVPNProcess(helper_command=(str(fake), "connect"))
    logs = []

    process.connect(profile, password="secret", on_log=logs.append)
    deadline = time.monotonic() + 5
    while process.status().state != VPNConnectionState.CONNECTED and time.monotonic() < deadline:
        time.sleep(0.05)

    request = json.loads(logs[0].removeprefix("REQUEST "))
    assert request == {"host": "vpn.example.com", "port": 443, "username": "demo"}
    assert not any("secret" in line for line in logs)

    started = time.monotonic()
    process.disconnect()
    assert time.monotonic() - started < 2
    assert process.status().state == VPNConnectionState.DISCONNECTED


def test_helper_mode_dry_run_shows_helper_and_openfortivpn_command():
    profile = VPNProfile(name="Demo", backend="openfortivpn", host="vpn.example.com", port=443)

    command = OpenFortiVPNProcess(helper_command=("pkexec", "/h", "connect")).connect(
        profile, dry_run=True
    )

    assert command[:4] == ["pkexec", "/h", "connect", "→"]
    assert command[4:6] == ["openfortivpn", "vpn.example.com:443"]
