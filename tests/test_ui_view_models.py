from vpn_doctor.models.status import VPNConnectionState, VPNStatus
from vpn_doctor.ui.view_models import ConnectionStatusViewModel, ConnectionTimer, format_elapsed


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


def test_view_model_failed_prefers_suggestion():
    status = VPNStatus(
        backend="openfortivpn",
        state=VPNConnectionState.FAILED,
        message="ERROR:  Could not authenticate to gateway.",
        suggestion="Check the password.",
    )
    vm = ConnectionStatusViewModel.from_status(status)

    assert vm.subtitle == "Check the password."


def test_format_elapsed():
    assert format_elapsed(0) == "00:00:00"
    assert format_elapsed(3725.9) == "01:02:05"


def test_connection_timer_runs_only_while_connected():
    timer = ConnectionTimer()

    assert timer.update(VPNConnectionState.CONNECTING, now=10.0) is None
    assert timer.update(VPNConnectionState.CONNECTED, now=20.0) == "00:00:00"
    assert timer.update(VPNConnectionState.CONNECTED, now=81.0) == "00:01:01"
    assert timer.update(VPNConnectionState.DISCONNECTED, now=90.0) is None
    assert timer.update(VPNConnectionState.CONNECTED, now=100.0) == "00:00:00"


def test_view_model_waiting_for_prompt():
    status = VPNStatus(
        backend="openfortivpn",
        state=VPNConnectionState.CONNECTING,
        prompt="Two-factor authentication token:",
    )
    vm = ConnectionStatusViewModel.from_status(status)

    assert vm.title == "Waiting for you"
    assert vm.subtitle == "Two-factor authentication token:"
    assert vm.can_disconnect is True


def test_view_model_pills():
    connected = VPNStatus(backend="networkmanager", state=VPNConnectionState.CONNECTED)
    failed = VPNStatus(backend="networkmanager", state=VPNConnectionState.FAILED)

    assert ConnectionStatusViewModel.from_status(connected).pill == "● ONLINE"
    assert ConnectionStatusViewModel.from_status(failed).pill == "✕ FAILURE"
