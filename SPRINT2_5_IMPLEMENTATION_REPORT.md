# Sprint 2.5 Implementation Report

## Summary

Sprint 2.5 wires the GTK UI to the backend. It also repairs `dev`, where the
Sprint 2.3 code had never been merged although Sprint 2.4 depended on it.

## Fixed

- `vpn-doctor profiles` and `vpn-doctor connect --wait` crashed with
  `AttributeError`: Sprint 2.3 lived on `feature/openfortivpn-process-manager`
  and was not merged. Profile loading and the wait loop are restored, with
  tests on both CLI paths.
- The log parser did not recognize the messages printed by openfortivpn 1.23.
  A wrong password now reads as an authentication failure, with a suggestion,
  instead of a generic error.
- A wrong password used to end as `disconnected`: openfortivpn prints
  `Closed connection to gateway.` after the failure. The state now stays
  `failed`.
- The GUI joined log lines with a literal `\n`.

## Added

- `pkexec` privilege escalation, documented in ADR-0010.
- `-c /dev/null` so `/etc/openfortivpn/config` is never merged into a profile.
- Profiles loaded from `~/.config/vpn-doctor/profiles.json`; files that
  contain a password are rejected.
- GUI: password dialog (never stored), live logs, status refresh, failure
  suggestion, connection timer, Diagnose button, disconnect on shutdown.
- End-to-end test with a fake `openfortivpn` executable.

## Removed

- The accidental nested copy of the repository in `vpn-doctor/`.
- `SPRINT2_4_TEST_RESULT.txt`, which contained output from the generation
  sandbox.

## Validation

```bash
ruff check src tests
pytest            # 51 passed
vpn-doctor gui    # starts without errors on Fedora 44, libadwaita 1.9
```

Not yet validated against a real FortiGate gateway from the GUI.

## Review notes

- Disconnecting triggers a second polkit prompt (see ADR-0010, future work).
- The GUI asks for the password at each connection. Secret Service storage is
  planned for Sprint 4.
- `connect --wait` without the GUI leaves openfortivpn running after a
  timeout; the CLI lifecycle needs a foreground mode.
- Only the first profile is used; the profile selector is still to do.
