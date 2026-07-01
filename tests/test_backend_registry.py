import pytest

from vpn_doctor.backend.errors import BackendNotFoundError
from vpn_doctor.backend.openfortivpn import OpenFortiVPNBackend
from vpn_doctor.backend.registry import BackendRegistry


def test_registry_registers_backend():
    registry = BackendRegistry()
    registry.register(OpenFortiVPNBackend())

    assert registry.names() == ["openfortivpn"]
    assert registry.get("openfortivpn").name == "openfortivpn"


def test_registry_raises_for_missing_backend():
    registry = BackendRegistry()

    with pytest.raises(BackendNotFoundError):
        registry.get("missing")
