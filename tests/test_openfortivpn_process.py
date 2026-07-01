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

    assert command == ["openfortivpn", "vpn.example.com:443", "-u", "demo"]
