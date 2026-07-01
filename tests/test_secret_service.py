from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.services.secret_service import EnvironmentSecretProvider


def test_environment_secret_provider_reads_password(monkeypatch):
    monkeypatch.setenv("VPN_DOCTOR_PASSWORD", "secret")
    profile = VPNProfile(name="Demo", backend="openfortivpn", host="vpn.example.com", port=443)

    assert EnvironmentSecretProvider().get_password(profile) == "secret"


def test_environment_secret_provider_returns_none_when_missing(monkeypatch):
    monkeypatch.delenv("VPN_DOCTOR_PASSWORD", raising=False)
    profile = VPNProfile(name="Demo", backend="openfortivpn", host="vpn.example.com", port=443)

    assert EnvironmentSecretProvider().get_password(profile) is None
