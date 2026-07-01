# OpenFortiVPN Backend Specification

## Purpose

The OpenFortiVPN backend wraps the `openfortivpn` command-line tool and normalizes its
behaviour for VPN Doctor.

The backend is responsible for:

- command construction;
- process execution;
- log parsing;
- status updates;
- lifecycle cleanup;
- backend-specific diagnostics.

## Current implementation

The current backend supports:

- safe command construction;
- basic log parsing;
- binary availability check;
- gateway TCP reachability check.

Real process lifecycle is intentionally not complete yet.

## Command construction rules

The backend must never include passwords in command arguments.

Allowed arguments:

- gateway host and port;
- username;
- trusted certificate fingerprint;
- realm when supported;
- config file path if safe.

Forbidden:

- password in argv;
- MFA token in argv;
- unredacted secret in log.

## Log parsing

Known OpenFortiVPN log lines include:

```text
INFO: Connected to gateway.
INFO: Authenticated.
INFO: Remote gateway has allocated a VPN.
INFO: Tunnel is up and running.
ERROR: Gateway certificate validation failed.
INFO: Connection terminated.
```

These must map to normalized states:

| Log signal | Normalized state |
| --- | --- |
| connected to gateway | connecting |
| authenticated | authenticating |
| allocated a VPN | configuring |
| tunnel is up | connected |
| certificate validation failed | failed |
| connection terminated | disconnected |

## Process lifecycle

Future process management should use `subprocess.Popen` with:

- stdout/stderr captured;
- line-by-line reading;
- cancellation support;
- cleanup on disconnect;
- timeout handling.

## Secrets

The backend must receive secrets from a secret service at runtime, not from `VPNProfile`.

## Diagnostics

Backend-specific diagnostics:

- `openfortivpn` installed;
- gateway TCP reachable;
- trusted certificate configured when needed;
- command can be built;
- backend version detectable;
- known error patterns parseable.

## Testing

Test with mocked subprocesses and sanitized log fixtures.

Do not require a real VPN for unit tests.
