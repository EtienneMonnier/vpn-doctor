import ipaddress
import json

from vpn_doctor.diagnostics.conflicts import (
    NetworkSnapshot,
    Route,
    find_conflicts,
    parse_ip_routes,
    parse_resolvectl_domains,
)

LAN = Route(ipaddress.ip_network("192.168.1.0/24"), "wlp2s0", 600, "link")
DEFAULT = Route(ipaddress.ip_network("0.0.0.0/0"), "wlp2s0", 600)
VPN_LINKS = {"tun0": "Office", "wg0": "Lab"}


def route(network, device, metric=50):
    return Route(ipaddress.ip_network(network), device, metric)


def names(items):
    return [item.name for item in items]


def test_parse_ip_routes():
    text = json.dumps(
        [
            {"dst": "default", "gateway": "192.0.2.1", "dev": "wlp2s0", "metric": 600},
            {"dst": "192.0.2.0/24", "dev": "wlp2s0", "scope": "link"},
            {"dst": "169.254.0.0/16", "dev": "wlp2s0", "scope": "link"},
        ]
    )

    routes = parse_ip_routes(text)

    assert [str(r.network) for r in routes] == ["0.0.0.0/0", "192.0.2.0/24"]
    assert routes[1].scope == "link"
    assert str(parse_ip_routes('[{"dst": "default", "dev": "wg0"}]', family=6)[0].network) == "::/0"


def test_parse_resolvectl_domains():
    text = "Global:\nLink 3 (wlp2s0): home\nLink 6 (wg0): ~.\nLink 7 (tun0): corp.example.com ~.\n"

    assert parse_resolvectl_domains(text) == {
        "wlp2s0": ["home"],
        "wg0": ["~."],
        "tun0": ["corp.example.com", "~."],
    }


def test_no_conflict_with_distinct_networks():
    snapshot = NetworkSnapshot(
        VPN_LINKS,
        [LAN, DEFAULT, route("10.10.0.0/16", "tun0"), route("10.20.0.0/16", "wg0")],
    )

    assert find_conflicts(snapshot) == []


def test_two_full_tunnels():
    snapshot = NetworkSnapshot(
        VPN_LINKS,
        [route("0.0.0.0/1", "tun0"), route("128.0.0.0/1", "tun0"), route("0.0.0.0/0", "wg0")],
    )

    items = find_conflicts(snapshot)

    assert names(items) == ["Two full tunnels"]
    assert "Lab and Office" in items[0].message


def test_overlapping_vpn_networks_names_the_winner():
    snapshot = NetworkSnapshot(VPN_LINKS, [route("10.0.0.0/8", "tun0"), route("10.41.0.0/16", "wg0")])

    items = find_conflicts(snapshot)

    assert names(items) == ["Overlapping VPN networks"]
    assert items[0].message.endswith("goes to Lab only.")


def test_vpn_overlapping_local_network():
    snapshot = NetworkSnapshot(VPN_LINKS, [LAN, route("192.168.0.0/16", "tun0")])

    items = find_conflicts(snapshot)

    assert names(items) == ["VPN overlaps your local network"]
    assert "192.168.1.0/24 on wlp2s0" in items[0].message


def test_host_route_to_vpn_gateway_is_not_a_conflict():
    gateway = Route(ipaddress.ip_network("198.51.100.7/32"), "wlp2s0", 600)
    snapshot = NetworkSnapshot(VPN_LINKS, [LAN, gateway, route("198.51.100.0/24", "tun0")])

    assert find_conflicts(snapshot) == []


def test_dns_claimed_by_two_vpns():
    snapshot = NetworkSnapshot(
        VPN_LINKS,
        dns_domains={"tun0": ["~."], "wg0": ["~."], "wlp2s0": ["home"]},
    )

    assert names(find_conflicts(snapshot)) == ["DNS claimed by several VPNs"]


def test_dns_catch_all_on_one_vpn_is_fine():
    snapshot = NetworkSnapshot(VPN_LINKS, dns_domains={"tun0": ["~."], "wg0": ["lab.example.com"]})

    assert find_conflicts(snapshot) == []


def test_conflicts_command(monkeypatch, capsys):
    from vpn_doctor.core.controller import ApplicationController

    snapshot = NetworkSnapshot(VPN_LINKS, [LAN, route("192.168.0.0/16", "tun0")])
    monkeypatch.setattr("vpn_doctor.core.controller.collect_snapshot", lambda links: snapshot)

    assert ApplicationController().run(["conflicts"]) == 1
    assert "VPN overlaps your local network" in capsys.readouterr().out
