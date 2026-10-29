from vpn_doctor.backend.log_parser import OpenFortiVPNLogParser, ParsedLogKind


def test_log_parser_connected_to_gateway():
    parser = OpenFortiVPNLogParser()
    parsed = parser.parse("INFO:   Connected to gateway.")
    assert parsed.kind == ParsedLogKind.CONNECTING


def test_log_parser_authenticated():
    parser = OpenFortiVPNLogParser()
    parsed = parser.parse("INFO:   Authenticated.")
    assert parsed.kind == ParsedLogKind.AUTHENTICATED


def test_log_parser_tunnel_up():
    parser = OpenFortiVPNLogParser()
    parsed = parser.parse("INFO:   Tunnel is up and running.")
    assert parsed.kind == ParsedLogKind.TUNNEL_UP


def test_log_parser_certificate_error():
    parser = OpenFortiVPNLogParser()
    parsed = parser.parse("ERROR:  Gateway certificate validation failed")
    assert parsed.kind == ParsedLogKind.CERTIFICATE_ERROR


def test_log_parser_wrong_password():
    parser = OpenFortiVPNLogParser()
    parsed = parser.parse(
        "ERROR:  Could not authenticate to gateway. Please check the password, "
        "client certificate, etc."
    )
    assert parsed.kind == ParsedLogKind.AUTHENTICATION_ERROR


def test_log_parser_tunnel_mode_refused():
    parser = OpenFortiVPNLogParser()
    parsed = parser.parse(
        "ERROR:  Could not authenticate to the gateway. Please make sure tunnel mode "
        "is allowed by the gateway, check the realm, etc."
    )
    assert parsed.kind == ParsedLogKind.AUTHENTICATION_ERROR


def test_log_parser_missing_root_privileges():
    parser = OpenFortiVPNLogParser()
    parsed = parser.parse(
        "ERROR:  This process was not spawned with root privileges, which are required."
    )
    assert parsed.kind == ParsedLogKind.PRIVILEGE_ERROR


def test_log_parser_unresolvable_gateway():
    parser = OpenFortiVPNLogParser()
    parsed = parser.parse("ERROR:  getaddrinfo: Name or service not known")
    assert parsed.kind == ParsedLogKind.GATEWAY_ERROR


def test_log_parser_certificate_success_is_not_an_error():
    parser = OpenFortiVPNLogParser()
    parsed = parser.parse("DEBUG:  Gateway certificate validation succeeded.")
    assert parsed.kind == ParsedLogKind.UNKNOWN
