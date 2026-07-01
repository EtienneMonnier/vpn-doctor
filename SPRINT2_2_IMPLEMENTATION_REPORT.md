# Sprint 2.2 Implementation Report

## Summary

Sprint 2.2 introduces the first real backend lifecycle components for VPN Doctor.

## Added

- Backend registry
- Backend manager
- OpenFortiVPN process abstraction
- Generic process runner
- OpenFortiVPN log parser
- Connection state machine
- Backend events and backend errors
- CLI commands:
  - `vpn-doctor status`
  - `vpn-doctor connect --dry-run`
  - `vpn-doctor disconnect`

## Safety

The sprint does not store secrets and does not commit real VPN profiles.

The `connect` command supports `--dry-run` for safe validation of command construction.

## Validation

Run:

```bash
python -m pip install -e .
pytest -v --tb=short
vpn-doctor --version
vpn-doctor profiles
vpn-doctor diagnose
vpn-doctor status
vpn-doctor connect --dry-run
```

## Next Sprint

Sprint 2.3 should add interactive password handling, safe real process start/stop,
and later GNOME Keyring integration.
