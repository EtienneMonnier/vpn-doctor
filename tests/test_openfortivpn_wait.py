from vpn_doctor.backend.openfortivpn_process import OpenFortiVPNProcess
from vpn_doctor.models.status import VPNConnectionState


def test_wait_until_terminal_returns_connected_after_log():
    process = OpenFortiVPNProcess()
    process._handle_line("INFO:   Tunnel is up and running.")

    status = process.wait_until_terminal_or_connected(timeout_seconds=0.1)

    assert status.state == VPNConnectionState.CONNECTED


def test_wait_until_terminal_times_out_when_no_process():
    process = OpenFortiVPNProcess()

    status = process.wait_until_terminal_or_connected(timeout_seconds=0.1)

    assert status.state in {
        VPNConnectionState.DISCONNECTED,
        VPNConnectionState.FAILED,
    }
