# Sprint 2 Specification - OpenFortiVPN Backend

## Objective

Design and prepare the OpenFortiVPN backend for a safe real connection lifecycle.

Sprint 2 focuses on:

- command construction;
- log parsing;
- status normalization;
- state machine design;
- process lifecycle design;
- diagnostic integration;
- tests.

## Non-goals

Sprint 2 should not yet implement a full polished GUI.

Sprint 2 should not store VPN passwords.

Sprint 2 should not embed real customer VPN data.

## Functional requirements

The backend must be able to:

1. Build an `openfortivpn` command without secrets.
2. Parse common `openfortivpn` log lines.
3. Normalize backend states.
4. Run safe diagnostics.
5. Report missing binaries.
6. Report unreachable gateways.
7. Detect certificate validation failures from logs.
8. Provide enough events for a future GUI.

## Future connection command

The command should be built like:

```text
openfortivpn vpn.example.com:44443 -u demo-user --trusted-cert abcdef...
```

Passwords must not appear in command arguments.

## Acceptance criteria

- Existing tests pass.
- New backend tests pass.
- No secrets appear in test fixtures.
- `vpn-doctor diagnose` still works.
- `vpn-doctor profiles` still works.
- Documentation and ADRs are updated.

## Suggested commit

```text
feat: prepare OpenFortiVPN backend lifecycle
```
