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


class _ExitedProcess:
    def poll(self):
        return 1


def test_status_reports_disconnected_when_process_exits():
    process = OpenFortiVPNProcess()
    process.state_machine.transition(VPNConnectionState.CONNECTING, "Starting openfortivpn")
    process.runner.process = _ExitedProcess()

    status = process.status()

    assert status.state == VPNConnectionState.DISCONNECTED
    assert status.message == "openfortivpn process exited"


def test_status_keeps_failure_when_process_exits_after_error():
    process = OpenFortiVPNProcess()
    process._handle_line("ERROR:  Could not connect to gateway (Connection refused).")
    process.runner.process = _ExitedProcess()

    assert process.status().state == VPNConnectionState.FAILED
