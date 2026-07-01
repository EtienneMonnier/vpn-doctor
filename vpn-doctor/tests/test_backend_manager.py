from vpn_doctor.backend.manager import BackendManager
from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.models.status import VPNConnectionState


def test_backend_manager_default_registry() -> None:
    manager = BackendManager()
    profile = VPNProfile(name="demo", backend="openfortivpn", host="vpn.example.com", port=443)

    status = manager.status(profile)

    assert status.backend == "openfortivpn"
    assert status.state == VPNConnectionState.DISCONNECTED


def test_backend_manager_connect_dry_run() -> None:
    manager = BackendManager()
    profile = VPNProfile(name="demo", backend="openfortivpn", host="vpn.example.com", port=443)

    status = manager.connect(profile, dry_run=True)

    assert status.state == VPNConnectionState.DISCONNECTED
    assert "Dry run" in status.message
