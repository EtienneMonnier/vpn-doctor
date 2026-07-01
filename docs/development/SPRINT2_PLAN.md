# Sprint 2 Plan - OpenFortiVPN Backend

## Goal

Build the OpenFortiVPN backend foundation without introducing a GUI.

## Deliverables

- Backend lifecycle design.
- Command builder.
- Log parser.
- Status mapping.
- Diagnostics kept safe and non-destructive.
- Tests for parsing and diagnostics.

## Out of scope

- GTK UI.
- Stored passwords.
- Automatic repair.
- Multi-backend registry.

## Acceptance criteria

```bash
vpn-doctor --version
vpn-doctor profiles
vpn-doctor diagnose
pytest
```

All commands must work without a real VPN account.
