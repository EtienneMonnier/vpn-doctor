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


def test_state_machine_explains_wrong_password():
    parser = OpenFortiVPNLogParser()
    machine = ConnectionStateMachine()

    machine.apply_log(parser.parse("INFO:   Connected to gateway."))
    machine.apply_log(
        parser.parse("ERROR:  Could not authenticate to gateway. Please check the password.")
    )
    machine.apply_log(parser.parse("INFO:   Closed connection to gateway."))
    machine.apply_log(parser.parse("ERROR:  Some follow-up error."))

    assert machine.state == VPNConnectionState.FAILED
    assert machine.suggestion is not None
    assert "password" in machine.suggestion


def test_state_machine_clears_suggestion_on_new_attempt():
    parser = OpenFortiVPNLogParser()
    machine = ConnectionStateMachine()

    machine.apply_log(parser.parse("ERROR:  getaddrinfo: Name or service not known"))
    machine.transition(VPNConnectionState.CONNECTING, "Starting openfortivpn")

    assert machine.suggestion is None


def test_state_machine_stays_failed_after_gateway_closes_connection():
    parser = OpenFortiVPNLogParser()
    machine = ConnectionStateMachine()

    machine.apply_log(parser.parse("ERROR:  Could not authenticate to gateway."))
    machine.apply_log(parser.parse("INFO:   Closed connection to gateway."))

    assert machine.state == VPNConnectionState.FAILED
