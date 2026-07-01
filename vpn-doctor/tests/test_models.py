from vpn_doctor.models.diagnostic import DiagnosticItem, DiagnosticReport
from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.models.status import VPNConnectionState, VPNStatus


def test_diagnostic_report_success() -> None:
    report = DiagnosticReport.from_items(
        "test",
        [DiagnosticItem(name="a", success=True, message="ok")],
    )

    assert report.success is True


def test_diagnostic_report_failure() -> None:
    report = DiagnosticReport.from_items(
        "test",
        [DiagnosticItem(name="a", success=False, message="bad")],
    )

    assert report.success is False


def test_profile_does_not_require_secret() -> None:
    profile = VPNProfile(name="demo", backend="openfortivpn", host="vpn.example.com", port=443)

    assert profile.username is None
    assert profile.trusted_cert is None


def test_status_model() -> None:
    status = VPNStatus(backend="openfortivpn", state=VPNConnectionState.DISCONNECTED)

    assert status.state == VPNConnectionState.DISCONNECTED
