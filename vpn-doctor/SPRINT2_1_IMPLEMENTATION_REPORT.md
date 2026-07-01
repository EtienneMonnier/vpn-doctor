# Sprint 2.1 Implementation Report

## Scope

Sprint 2.1 introduces the first real OpenFortiVPN process-management foundation.

This is still intentionally conservative: the code can build commands, start a process through an injectable runner, parse OpenFortiVPN logs, update normalized VPN status, and stop a process cleanly. Real production profile storage and desktop UI integration remain future work.

## Added

- `BackendManager`
- `BackendRegistry`
- `ProcessRunner`
- `OpenFortiVPNProcess`
- `OpenFortiVPNLogParser`
- CLI commands:
  - `vpn-doctor status`
  - `vpn-doctor connect --dry-run`
  - `vpn-doctor connect --foreground`
  - `vpn-doctor connect --ask-password`
  - `vpn-doctor disconnect`
- Unit tests for:
  - backend manager
  - dry-run process start
  - log-driven state updates
  - graceful process stop

## Safety Constraints

- Passwords are never embedded in command arguments.
- Tests do not start real VPN processes.
- `--dry-run` is available for safe validation.
- Real profiles are still placeholders.

## Test Result

```text
13 passed
```

## Next Step

Sprint 2.2 should add persistent runtime state, a PID/session manager, better profile loading, and safer CLI semantics for long-running VPN sessions.
