from vpn_doctor.backend.openfortivpn import OpenFortiVPNBackend, OpenFortiVPNLogParser
from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.models.status import VPNConnectionState


def test_build_command_does_not_include_password() -> None:
    backend = OpenFortiVPNBackend()
    profile = VPNProfile(
        name="demo",
        backend="openfortivpn",
        host="vpn.example.com",
        port=44443,
        username="demo-user",
        trusted_cert="abc123",
    )

    command = backend.build_command(profile)

    assert command.argv == [
        "openfortivpn",
        "vpn.example.com:44443",
        "-u",
        "demo-user",
        "--trusted-cert",
        "abc123",
    ]
    assert "password" not in " ".join(command.argv).lower()


def test_log_parser_connected() -> None:
    parser = OpenFortiVPNLogParser()

    assert parser.parse_state("INFO:   Tunnel is up and running.") == VPNConnectionState.CONNECTED


def test_log_parser_certificate_failure() -> None:
    parser = OpenFortiVPNLogParser()

    assert (
        parser.parse_state("ERROR: Gateway certificate validation failed")
        == VPNConnectionState.FAILED
    )
