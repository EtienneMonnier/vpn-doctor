"""Detect conflicts between active VPNs and the local network.

Neither GNOME nor NetworkManager warns when two VPNs, or a VPN and the local
network, claim the same addresses. Traffic then silently goes to one side.

The checks work on a snapshot of the kernel routing table and of the
systemd-resolved DNS domains, so they are pure and easy to test.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from itertools import combinations

from vpn_doctor.models.diagnostic import DiagnosticItem, DiagnosticSeverity

LOGGER = logging.getLogger(__name__)

Network = ipaddress.IPv4Network | ipaddress.IPv6Network

# A full tunnel is a default route, or the 0/1 + 128/1 pair used by OpenVPN.
FULL_TUNNEL_PREFIXES = {
    ipaddress.ip_network("0.0.0.0/0"),
    ipaddress.ip_network("0.0.0.0/1"),
    ipaddress.ip_network("128.0.0.0/1"),
    ipaddress.ip_network("::/0"),
    ipaddress.ip_network("::/1"),
    ipaddress.ip_network("8000::/1"),
}

IGNORED_NETWORKS = (
    ipaddress.ip_network("fe80::/10"),  # link-local
    ipaddress.ip_network("ff00::/8"),  # multicast
    ipaddress.ip_network("224.0.0.0/4"),  # multicast
    ipaddress.ip_network("169.254.0.0/16"),  # link-local
)

_RESOLVECTL_LINK = re.compile(r"^Link \d+ \(([^)]+)\):\s*(.*)$")


# Tunnels started outside NetworkManager: openfortivpn (ppp), wg-quick, openvpn.
UNMANAGED_TUNNEL_PREFIXES = ("ppp", "tun", "wg")


@dataclass(frozen=True)
class Route:
    network: Network
    device: str
    metric: int = 0
    # "link" for networks directly attached to the interface.
    scope: str = ""


@dataclass
class NetworkSnapshot:
    """Routes and DNS domains, plus which interfaces belong to which VPN."""

    vpn_links: dict[str, str]
    routes: list[Route] = field(default_factory=list)
    dns_domains: dict[str, list[str]] = field(default_factory=dict)


def parse_ip_routes(text: str, family: int = 4) -> list[Route]:
    """Parse `ip -j -4 route show` or `ip -j -6 route show` output."""
    routes = []
    for raw in json.loads(text or "[]"):
        destination = raw.get("dst", "")
        if destination == "default":
            destination = "0.0.0.0/0" if family == 4 else "::/0"
        try:
            network = ipaddress.ip_network(destination, strict=False)
        except ValueError:
            continue
        if any(network.version == n.version and network.subnet_of(n) for n in IGNORED_NETWORKS):
            continue
        routes.append(
            Route(
                network,
                raw.get("dev", ""),
                int(raw.get("metric", 0) or 0),
                raw.get("scope", ""),
            )
        )
    return routes


def parse_resolvectl_domains(text: str) -> dict[str, list[str]]:
    """Parse `resolvectl domain` output into {interface: [domains]}."""
    domains = {}
    for line in text.splitlines():
        match = _RESOLVECTL_LINK.match(line.strip())
        if match:
            domains[match.group(1)] = match.group(2).split()
    return domains


def find_conflicts(snapshot: NetworkSnapshot) -> list[DiagnosticItem]:
    """Return the conflicts found in the snapshot, the most serious first."""
    vpn = snapshot.vpn_links
    vpn_routes = [r for r in snapshot.routes if r.device in vpn]
    # Only directly attached networks: host routes to VPN gateways are expected.
    lan_routes = [r for r in snapshot.routes if r.device not in vpn and r.scope == "link"]

    items: list[DiagnosticItem] = []
    items.extend(_full_tunnels(vpn, vpn_routes))
    items.extend(_overlaps_between_vpns(vpn, vpn_routes))
    items.extend(_overlaps_with_lan(vpn, vpn_routes, lan_routes))
    items.extend(_dns_catch_all(vpn, snapshot.dns_domains))
    return items


def _full_tunnels(vpn: dict[str, str], routes: list[Route]) -> list[DiagnosticItem]:
    devices = sorted({r.device for r in routes if r.network in FULL_TUNNEL_PREFIXES})
    if len(devices) < 2:
        return []
    names = " and ".join(sorted(vpn[d] for d in devices))
    return [
        DiagnosticItem(
            "Two full tunnels",
            False,
            f"{names} both want to carry all your traffic. Only one of them really does.",
            "Keep one full-tunnel VPN, or ask for split tunneling on the other one.",
            DiagnosticSeverity.ERROR,
        )
    ]


def _overlaps_between_vpns(vpn: dict[str, str], routes: list[Route]) -> list[DiagnosticItem]:
    specific = [r for r in routes if r.network not in FULL_TUNNEL_PREFIXES]
    items = []
    seen = set()
    for first, second in combinations(specific, 2):
        if first.device == second.device or not _overlap(first.network, second.network):
            continue
        key = frozenset((first.network, second.network))
        if key in seen:
            continue
        seen.add(key)
        winner = _winner(first, second)
        items.append(
            DiagnosticItem(
                "Overlapping VPN networks",
                False,
                f"{vpn[first.device]} routes {first.network} and {vpn[second.device]} routes "
                f"{second.network}. Traffic for the overlap goes to {vpn[winner.device]} only.",
                "Disconnect one of these VPNs to reach hosts of the other one, or ask an "
                "administrator to use distinct address ranges.",
                DiagnosticSeverity.WARNING,
            )
        )
    return items


def _overlaps_with_lan(
    vpn: dict[str, str],
    vpn_routes: list[Route],
    lan_routes: list[Route],
) -> list[DiagnosticItem]:
    items = []
    for route in vpn_routes:
        if route.network in FULL_TUNNEL_PREFIXES:
            continue
        for lan in lan_routes:
            if _overlap(route.network, lan.network):
                items.append(
                    DiagnosticItem(
                        "VPN overlaps your local network",
                        False,
                        f"{vpn[route.device]} routes {route.network}, which overlaps your local "
                        f"network {lan.network} on {lan.device}.",
                        "Devices of your local network (router, printer, NAS) or remote hosts may "
                        "become unreachable. Renumbering the local network avoids it, e.g. "
                        "192.168.77.0/24 instead of 192.168.1.0/24.",
                        DiagnosticSeverity.WARNING,
                    )
                )
    return items


def _dns_catch_all(vpn: dict[str, str], domains: dict[str, list[str]]) -> list[DiagnosticItem]:
    catch_all = sorted(link for link in vpn if "~." in domains.get(link, []))
    if len(catch_all) < 2:
        return []
    names = " and ".join(sorted(vpn[link] for link in catch_all))
    return [
        DiagnosticItem(
            "DNS claimed by several VPNs",
            False,
            f"{names} both ask to resolve every name. Answers may come from either VPN, so "
            "internal names can fail at random.",
            "Configure routing-only DNS domains (e.g. ~corp.example.com) on one of them in "
            "the connection settings, under IPv4 > DNS search domains.",
            DiagnosticSeverity.WARNING,
        )
    ]


def _overlap(first: Network, second: Network) -> bool:
    return first.version == second.version and first.overlaps(second)


def _winner(first: Route, second: Route) -> Route:
    """Longest prefix wins; on a tie, the lowest metric."""
    if first.network.prefixlen != second.network.prefixlen:
        return first if first.network.prefixlen > second.network.prefixlen else second
    return first if first.metric <= second.metric else second


def collect_snapshot(vpn_links: dict[str, str]) -> NetworkSnapshot:
    """Read the current routes and DNS domains of the system."""
    routes: list[Route] = []
    for family in (4, 6):
        output = _run(["ip", "-j", f"-{family}", "route", "show"])
        routes.extend(parse_ip_routes(output or "[]", family))

    links = dict(vpn_links)
    for route in routes:
        if route.device not in links and route.device.startswith(UNMANAGED_TUNNEL_PREFIXES):
            links[route.device] = route.device

    domains = {}
    if shutil.which("resolvectl"):
        domains = parse_resolvectl_domains(_run(["resolvectl", "domain"]))
    return NetworkSnapshot(vpn_links=links, routes=routes, dns_domains=domains)


def _run(command: list[str]) -> str:
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=5,
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        LOGGER.warning("Cannot run %s: %s", command[0], exc)
        return ""
