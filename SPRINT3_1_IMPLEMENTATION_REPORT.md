# Sprint 3.1 Implementation Report

## Summary

First Sprint 3 diagnostic: a Remote Desktop server reached through the VPN.
See the case study `docs/case-studies/rdp-licensing-behind-wireguard.md`.

## Added

- `vpn-doctor rdp HOST [--port PORT] [--log FILE|-]`.
- `diagnostics/rdp.py`: credential-free probe (TCP, X.224 negotiation, TLS)
  and FreeRDP/Remmina log analysis. Every error marker was checked against
  the strings shipped in FreeRDP 3.
- Client certificate paths in profiles (`user_cert`, `user_key`), passed to
  openfortivpn as `--user-cert` / `--user-key`.

## Safety

- The probe sends no credentials.
- The log analysis never prints raw log lines.

## Validation

```bash
ruff check src tests
pytest            # 63 passed
journalctl --user -b -o cat | vpn-doctor rdp <host> --log -
```

Validated against the real case that motivated it.

## Review notes

- The RDP check is CLI only; a GUI report view comes with the diagnostics
  engine.
- `--log -` reads the whole boot journal; a `--since` filter may help.
