from vpn_doctor.models.status import VPNConnectionState, VPNStatus
from vpn_doctor.ui.view_models import ConnectionStatusViewModel


def test_view_model_disconnected():
    status = VPNStatus(backend="openfortivpn", state=VPNConnectionState.DISCONNECTED)
    vm = ConnectionStatusViewModel.from_status(status)

    assert vm.title == "Disconnected"
    assert vm.can_connect is True
    assert vm.can_disconnect is False


def test_view_model_connected():
    status = VPNStatus(backend="openfortivpn", state=VPNConnectionState.CONNECTED)
    vm = ConnectionStatusViewModel.from_status(status)

    assert vm.title == "Connected"
    assert vm.can_connect is False
    assert vm.can_disconnect is True


def test_view_model_failed():
    status = VPNStatus(backend="openfortivpn", state=VPNConnectionState.FAILED, message="Boom")
    vm = ConnectionStatusViewModel.from_status(status)

    assert vm.title == "Failed"
    assert vm.subtitle == "Boom"
    assert vm.css_class == "error"
