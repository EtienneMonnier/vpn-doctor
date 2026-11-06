from vpn_doctor.backend.networkmanager import parse_wireguard_endpoint
from vpn_doctor.diagnostics.latency import (
    LatencyQuality,
    LatencyResult,
    classify,
    describe,
    parse_ping_output,
    tunnel_target,
)

PING_OK = """PING 192.0.2.10 (192.0.2.10) 56(84) bytes of data.

--- 192.0.2.10 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss, time 802ms
rtt min/avg/max/mdev = 28.332/30.412/36.147/2.943 ms
"""

PING_LOST = """PING 192.0.2.1 (192.0.2.1) 56(84) bytes of data.

--- 192.0.2.1 ping statistics ---
5 packets transmitted, 0 received, 100% packet loss, time 808ms
"""


def result(average, jitter=1.0, received=5):
    return LatencyResult("192.0.2.10", "ping", 5, received, average, jitter)


def test_parse_ping_output_reads_average_jitter_and_loss():
    parsed = parse_ping_output("192.0.2.10", PING_OK)
    assert parsed.average_ms == 30.412
    assert parsed.jitter_ms == 2.943
    assert parsed.loss_percent == 0
    assert parsed.answered


def test_parse_ping_output_without_answer():
    parsed = parse_ping_output("192.0.2.1", PING_LOST)
    assert parsed.loss_percent == 100
    assert not parsed.answered


def test_parse_ping_output_rejects_garbage():
    assert parse_ping_output("192.0.2.1", "ping: unknown host") is None


def test_classify_thresholds():
    assert classify(result(20)) == LatencyQuality.GOOD
    assert classify(result(80)) == LatencyQuality.FAIR
    assert classify(result(20, jitter=30)) == LatencyQuality.FAIR
    assert classify(result(200)) == LatencyQuality.POOR
    assert classify(result(20, jitter=60)) == LatencyQuality.POOR
    assert classify(result(20, received=4)) == LatencyQuality.POOR


def test_describe_good_and_poor():
    good = describe("Tunnel latency", result(30), inside_tunnel=True)
    assert good.success and "30 ms" in good.message and good.suggestion is None

    poor = describe("Gateway latency", result(300), inside_tunnel=False)
    assert not poor.success and poor.suggestion


def test_silent_gateway_is_not_an_error_but_silent_tunnel_is():
    silent = LatencyResult("192.0.2.1", "ping", 5, 0)
    assert describe("Gateway latency", silent, inside_tunnel=False).success
    assert not describe("Tunnel latency", silent, inside_tunnel=True).success


def test_tunnel_target_prefers_the_ppp_peer():
    addresses = [{"family": "inet", "local": "10.0.0.2", "address": "192.0.2.254"}]
    assert tunnel_target(addresses, []) == "192.0.2.254"


def test_tunnel_target_uses_a_wireguard_host_route():
    addresses = [{"family": "inet", "local": "10.0.8.4"}]
    routes = [{"dst": "10.0.8.4"}, {"dst": "10.0.8.1"}, {"dst": "10.0.9.0/24"}]
    assert tunnel_target(addresses, routes) == "10.0.8.1"


def test_tunnel_target_without_candidate():
    assert tunnel_target([{"family": "inet", "local": "10.0.0.2"}], [{"dst": "10.0.0.0/24"}]) is None


def test_parse_wireguard_endpoint():
    peers = "abcdef= allowed-ips=10.0.0.1/32 endpoint=192.0.2.7\\:51820"
    assert parse_wireguard_endpoint(peers) == ("192.0.2.7", 51820)
    assert parse_wireguard_endpoint("abcdef= endpoint=[2001:db8::1]\\:51820") == ("2001:db8::1", 51820)
    assert parse_wireguard_endpoint("abcdef= allowed-ips=10.0.0.1/32") == ("", 0)
