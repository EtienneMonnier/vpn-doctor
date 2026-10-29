# Sprint 4.1 Implementation Report

## Summary

VPN Doctor becomes a NetworkManager overlay (ADR-0011) and gets a new UI with
custom skins.

## Added

- NetworkManager backend: discovers VPN and WireGuard connections, connects
  and disconnects them through `nmcli`, follows the journal during a session.
- Failure explanations from the NetworkManager reason and the VPN plugin log
  (OpenVPN, OpenConnect, openfortivpn). Markers were checked against the
  installed binaries.
- Profile selection: `--profile NAME` in the CLI, a selector in the UI.
- UI redesign: status panel with pill and timer, connection panel, log console.
- Skins: GTK CSS files with metadata, live reload, user skins in
  `~/.config/vpn-doctor/themes/`; built-in "Wasteland Terminal" skin.

## Changed

- Backend `status()` and `disconnect()` receive the profile.
- `diagnostics/log_rules.py` is shared by the RDP and NetworkManager
  explanations.
- Tests hide the developer's real NetworkManager connections behind an empty
  fake `nmcli`.

## Validation

```bash
ruff check src tests
pytest            # 87 passed
vpn-doctor profiles
```

The UI was rendered with both skins on Fedora 44 (GTK 4.22, libadwaita 1.9).
Real activation of a NetworkManager connection from the UI is still to be
validated by hand.

## Review notes

- Status is polled with `nmcli` every 500 ms; libnm signals could replace it.
- The journal follower assumes the user can read the NetworkManager journal.
- Profile discovery runs once; the ↻ button reloads it.
- Skins on libadwaita < 1.6 rely on the named colors only.
