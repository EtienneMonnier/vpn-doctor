from vpn_doctor.models.status import VPNConnectionState, VPNStatus
from vpn_doctor.ui.view_models import (
    ConnectionStatusViewModel,
    ConnectionTimer,
    editor_environment,
    format_elapsed,
    tab_changes,
)


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


def test_boot_lines_report_real_checks():
    from vpn_doctor.ui.view_models import boot_lines

    lines = boot_lines("0.0.1", connections=4, networkmanager=True, keyring=False)

    assert lines[0] == "VPN DOCTOR 0.0.1"
    assert "NetworkManager… ONLINE" in lines
    assert "Keyring… UNAVAILABLE" in lines
    assert "Scanning connections… 4 found" in lines


def test_tab_changes_opens_a_tab_per_connection():
    assert tab_changes(["a", "b", "c"], [], set()) == (["a", "b", "c"], [])


def test_tab_changes_reopens_closed_tabs_and_drops_removed_connections():
    assert tab_changes(["a", "c"], ["a", "b"], set()) == (["c"], ["b"])


def test_tab_changes_keeps_the_tab_of_an_active_removed_connection():
    assert tab_changes(["a"], ["a", "b"], {"b"}) == ([], [])


def test_editor_environment_follows_a_dark_window():
    assert editor_environment(True, {}) == {"GTK_THEME": "Adwaita:dark"}


def test_editor_environment_leaves_light_windows_and_user_themes_alone():
    assert editor_environment(False, {}) == {}
    assert editor_environment(True, {"GTK_THEME": "Arc-Dark"}) == {}
