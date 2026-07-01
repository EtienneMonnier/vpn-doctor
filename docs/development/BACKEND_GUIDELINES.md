# Backend Guidelines

## Purpose

Backends abstract VPN engines.

The UI and services must not care whether the connection uses OpenFortiVPN, WireGuard, OpenVPN or another tool.

## Backend responsibilities

A backend should:

- Validate required binaries.
- Start connection.
- Stop connection.
- Parse logs.
- Report status.
- Provide backend-specific diagnostics.
- Avoid leaking secrets.

## Minimal interface

```python
class VPNBackend:
    def connect(self, profile): ...
    def disconnect(self): ...
    def status(self): ...
    def diagnose(self, profile): ...
```

## OpenFortiVPN backend

Initial supported backend.

Important behavior learned from real case:

- Custom ports use `host:port`.
- Self-signed FortiGate certificates require `trusted-cert`.
- NetworkManager FortiSSLVPN may connect but fail to pass traffic.
- OpenFortiVPN can be more reliable than the NetworkManager plugin.

## Secret handling

Do not pass passwords in command-line arguments.

Command-line arguments are visible via `ps`.

Use:

- stdin
- keyring
- temporary in-memory handling

## Log parsing

OpenFortiVPN useful events:

- `Connected to gateway`
- `Authenticated`
- `Remote gateway has allocated a VPN`
- `Tunnel is up and running`
- `Gateway certificate validation failed`
- `Could not authenticate`
- `Connection terminated`
