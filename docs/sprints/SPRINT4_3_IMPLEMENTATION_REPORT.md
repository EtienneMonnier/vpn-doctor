# Sprint 4.3 Implementation Report

## Summary

Several VPNs at once, in tabs, with conflict detection.

## Added

- NetworkManager backend sessions: one nmcli call, journal follower and
  state machine per connection. Journal lines are read as JSON and plugin
  lines attributed through their syslog identifier (`nm-openvpn`...).
- `diagnostics/conflicts.py`: two full tunnels, overlapping VPN networks
  (naming the VPN that wins), VPN networks overlapping a directly attached
  local network, several VPNs claiming every DNS name (`~.`).
- `vpn-doctor conflicts`.
- UI: one tab per connection (`Adw.TabView`), `+` menu to open any
  connection, active connections opened at startup, tab marks (● ○ ✕) and
  loading indicator, conflict banner checked every 5 s.
- Controller methods accept an explicit profile.

## Validation

```bash
ruff check src tests
pytest            # 110 passed
vpn-doctor conflicts
```

The UI was rendered with both skins, three tabs and a simulated conflict.
Running two real VPNs at once is still to be validated by hand.

## Review notes

- Plugin helpers without an `nm-` identifier (pppd) are shown in every
  active tab, since they cannot be attributed.
- Only one direct openfortivpn tunnel can run at a time.
- Closing a tab never disconnects; the last tab cannot be closed.
- Conflict checks read the main routing table only; policy routing
  (WireGuard fwmark tables) is not analysed yet.
