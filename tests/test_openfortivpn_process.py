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
