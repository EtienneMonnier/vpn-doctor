from vpn_doctor.backend.log_parser import OpenFortiVPNLogParser
from vpn_doctor.backend.state_machine import ConnectionStateMachine
from vpn_doctor.models.status import VPNConnectionState


def test_state_machine_reaches_connected():
    parser = OpenFortiVPNLogParser()
    machine = ConnectionStateMachine()

    machine.apply_log(parser.parse("INFO:   Connected to gateway."))
    assert machine.state == VPNConnectionState.CONNECTING

    machine.apply_log(parser.parse("INFO:   Authenticated."))
    assert machine.state == VPNConnectionState.AUTHENTICATING

    machine.apply_log(parser.parse("INFO:   Tunnel is up and running."))
    assert machine.state == VPNConnectionState.CONNECTED


def test_state_machine_fails_on_certificate_error():
    parser = OpenFortiVPNLogParser()
    machine = ConnectionStateMachine()

    machine.apply_log(parser.parse("ERROR:  Gateway certificate validation failed"))
    assert machine.state == VPNConnectionState.FAILED
