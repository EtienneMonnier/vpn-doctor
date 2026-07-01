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
