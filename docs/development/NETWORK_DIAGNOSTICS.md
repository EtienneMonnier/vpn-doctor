# Network Diagnostics

## Checks

VPN Doctor should eventually perform:

- DNS resolution;
- TCP gateway reachability;
- route table inspection;
- DNS server inspection;
- interface inspection;
- MTU check;
- ping to expected internal host;
- internet reachability check;
- split tunnel vs full tunnel detection.

## Linux commands of interest

- `ip route`
- `ip addr`
- `resolvectl status`
- `journalctl`
- `tcpdump` for manual advanced troubleshooting only

## Caution

VPN Doctor should not require root for passive diagnostics where possible.

## Latency (implemented)

`src/vpn_doctor/diagnostics/latency.py` measures latency, not throughput: a
throughput test would transfer data, take long and disturb the tunnel.

- **Gateway latency**: 5 unprivileged pings (`ping -q -c 5 -i 0.2`, run with
  `LC_ALL=C` so the summary is parsed in English). When the gateway drops
  ping (frequent on FortiGate), the time to open a TCP connection to the
  gateway port is measured instead. No TCP fallback for WireGuard and OpenVPN,
  which usually listen on UDP. A silent gateway is information, not an error.
- **Tunnel latency** (connected only): 5 pings to the other side of the
  tunnel — the point-to-point peer of the pppd interface (openfortivpn), or
  the first host route of the interface that is not our own address
  (WireGuard). A silent tunnel is a warning: it is up but traffic does not flow.
- **Verdict**: good (≤ 50 ms and jitter ≤ 20 ms, no loss), poor (> 150 ms,
  jitter > 50 ms or any loss), fair otherwise. Jitter is ping's `mdev`.
  Comparing both lines tells whether slowness comes from the user's Internet
  access or from behind the VPN.

The checks run in `vpn-doctor diagnose` (and its `--json`), in the GUI
**Diagnose** button, and once in the GUI log when a tab becomes connected.
