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
