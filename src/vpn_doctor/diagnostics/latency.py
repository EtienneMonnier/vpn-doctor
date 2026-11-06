"""Latency checks: how fast the VPN gateway and the tunnel answer.

Latency is measured, not throughput: a throughput test would transfer data,
take long and disturb the tunnel. Five pings give the average round trip, its
variation (jitter) and the packet loss. Gateways that drop ping (frequent on
FortiGate) are measured by the time to open a TCP connection instead.

Parsing and classification are pure functions; only `measure_*` touch the
network.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass
from enum import StrEnum

from vpn_doctor.i18n import N_, _
from vpn_doctor.models.diagnostic import DiagnosticItem, DiagnosticSeverity

LOGGER = logging.getLogger(__name__)

PING_COUNT = 5
PING_INTERVAL = "0.2"  # the shortest interval allowed without root
PING_WAIT_SECONDS = 2
TCP_TIMEOUT_SECONDS = 3.0

# Average round trip (ms), jitter (ms) and loss (%) limits of each verdict.
GOOD_LATENCY_MS = 50.0
POOR_LATENCY_MS = 150.0
GOOD_JITTER_MS = 20.0
POOR_JITTER_MS = 50.0

_PACKETS = re.compile(r"(\d+) packets transmitted, (\d+) (?:packets )?received")
_RTT = re.compile(r"= ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms")


class LatencyQuality(StrEnum):
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


@dataclass(frozen=True)
class LatencyResult:
    """Round trips to one target, in milliseconds."""

    target: str
    method: str  # "ping" or "tcp"
    sent: int
    received: int
    average_ms: float | None = None
    jitter_ms: float | None = None

    @property
    def loss_percent(self) -> float:
        return 100.0 * (self.sent - self.received) / self.sent if self.sent else 100.0

    @property
    def answered(self) -> bool:
        return self.received > 0 and self.average_ms is not None


def parse_ping_output(target: str, output: str) -> LatencyResult | None:
    """Read the summary of `ping -q` (run with LC_ALL=C)."""
    packets = _PACKETS.search(output)
    if packets is None:
        return None
    rtt = _RTT.search(output)
    return LatencyResult(
        target=target,
        method="ping",
        sent=int(packets.group(1)),
        received=int(packets.group(2)),
        average_ms=float(rtt.group(2)) if rtt else None,
        jitter_ms=float(rtt.group(4)) if rtt else None,
    )


def classify(result: LatencyResult) -> LatencyQuality:
    average = result.average_ms or 0.0
    jitter = result.jitter_ms or 0.0
    loss = result.loss_percent
    if average > POOR_LATENCY_MS or jitter > POOR_JITTER_MS or loss > 0:
        return LatencyQuality.POOR
    if average > GOOD_LATENCY_MS or jitter > GOOD_JITTER_MS:
        return LatencyQuality.FAIR
    return LatencyQuality.GOOD


QUALITY_LABELS = {
    LatencyQuality.GOOD: N_("good"),
    LatencyQuality.FAIR: N_("fair"),
    LatencyQuality.POOR: N_("poor"),
}


def describe(name: str, result: LatencyResult | None, inside_tunnel: bool) -> DiagnosticItem:
    """Turn a measure into a diagnostic line with a verdict."""
    if result is None or not result.answered:
        if inside_tunnel:
            return DiagnosticItem(
                name=name,
                success=False,
                message=_("{target} does not answer through the tunnel").format(
                    target=result.target if result else "?"
                ),
                suggestion=_(
                    "The tunnel is up but traffic does not flow: check the routes, "
                    "or the firewall on the other side."
                ),
                severity=DiagnosticSeverity.WARNING,
            )
        return DiagnosticItem(
            name=name,
            success=True,
            message=_("{target} does not answer ping and no TCP port to measure").format(
                target=result.target if result else "?"
            ),
            suggestion=_("Many gateways block ping: this is not an error by itself."),
        )

    quality = classify(result)
    if result.method == "tcp":
        message = _("{quality}: {average:.0f} ms to {target} (TCP connection)").format(
            quality=_(QUALITY_LABELS[quality]), average=result.average_ms, target=result.target
        )
    else:
        message = _(
            "{quality}: {average:.0f} ms to {target}, jitter {jitter:.0f} ms, {loss:.0f}% loss"
        ).format(
            quality=_(QUALITY_LABELS[quality]),
            average=result.average_ms,
            target=result.target,
            jitter=result.jitter_ms or 0.0,
            loss=result.loss_percent,
        )

    suggestion = None
    if quality == LatencyQuality.POOR:
        suggestion = (
            _(
                "Slow or unstable tunnel: remote desktop and calls will lag. Compare with "
                "the gateway latency: if the gateway is fast, the slowness is behind the VPN."
            )
            if inside_tunnel
            else _(
                "Slow or unstable path to the gateway: check your own Internet "
                "connection (Wi-Fi, mobile data) before blaming the VPN."
            )
        )
    return DiagnosticItem(
        name=name,
        success=quality != LatencyQuality.POOR,
        message=message,
        suggestion=suggestion,
        severity=DiagnosticSeverity.WARNING if quality == LatencyQuality.POOR else DiagnosticSeverity.INFO,
    )


def measure_ping(target: str) -> LatencyResult | None:
    """Five unprivileged pings; None when ping is missing or fails to run."""
    if not shutil.which("ping"):
        return None
    command = [
        "ping", "-n", "-q",
        "-c", str(PING_COUNT),
        "-i", PING_INTERVAL,
        "-W", str(PING_WAIT_SECONDS),
        target,
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=PING_COUNT * PING_WAIT_SECONDS + 5,
            env={**os.environ, "LC_ALL": "C"},  # parse the English summary
        )
    except (OSError, subprocess.SubprocessError) as exc:
        LOGGER.warning("Cannot ping %s: %s", target, exc)
        return None
    return parse_ping_output(target, completed.stdout)


def measure_tcp(host: str, port: int, attempts: int = 3) -> LatencyResult:
    """Average time to open a TCP connection, for gateways that drop ping."""
    times = []
    for _attempt in range(attempts):
        start = time.monotonic()
        try:
            with socket.create_connection((host, port), timeout=TCP_TIMEOUT_SECONDS):
                times.append((time.monotonic() - start) * 1000.0)
        except OSError:
            continue
    average = sum(times) / len(times) if times else None
    return LatencyResult(
        target=f"{host}:{port}",
        method="tcp",
        sent=attempts,
        received=len(times),
        average_ms=average,
        jitter_ms=(max(times) - min(times)) / 2 if times else None,
    )


def measure_gateway(host: str, port: int = 0, tcp: bool = True) -> LatencyResult | None:
    """Ping the gateway; fall back to TCP when ping gets no answer."""
    result = measure_ping(host)
    if (result is None or not result.answered) and tcp and port:
        tcp_result = measure_tcp(host, port)
        if tcp_result.answered:
            return tcp_result
    if result is None:
        return LatencyResult(target=host, method="ping", sent=0, received=0)
    return result


def tunnel_target(addresses: list[dict], routes: list[dict]) -> str | None:
    """Pick an address on the other side of a tunnel interface.

    `addresses` and `routes` are the `addr_info` and route entries of
    `ip -j addr/route show dev IFACE`. A point-to-point peer (pppd) wins, then
    the first host route that is not one of our own addresses (WireGuard).
    """
    own = {entry.get("local") for entry in addresses}
    for entry in addresses:
        peer = entry.get("address")
        if entry.get("family") == "inet" and peer and peer not in own:
            return peer
    for route in routes:
        destination = route.get("dst", "")
        if destination and "/" not in destination and ":" not in destination and destination not in own:
            return destination
    return None


def interface_info(iface: str) -> tuple[list[dict], list[dict]]:
    """`addr_info` and IPv4 routes of one interface, from `ip -j`."""

    def run(*args: str) -> list:
        try:
            output = subprocess.run(
                ["ip", "-j", *args],
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=5,
                check=True,
            ).stdout
            return json.loads(output or "[]")
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            LOGGER.warning("Cannot read interface %s: %s", iface, exc)
            return []

    addresses = [entry for link in run("addr", "show", "dev", iface) for entry in link.get("addr_info", [])]
    return addresses, run("-4", "route", "show", "dev", iface)


def ppp_interfaces() -> list[str]:
    """Names of the pppd interfaces (openfortivpn runs pppd)."""
    try:
        names = os.listdir("/sys/class/net")
    except OSError:
        return []
    return sorted(name for name in names if name.startswith("ppp"))
