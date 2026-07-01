# Plugin System

## Goal

VPN Doctor should support multiple VPN engines without turning the codebase into a collection of special cases.

## Plugin responsibilities

A backend plugin should provide:

- metadata
- profile schema
- connect/disconnect implementation
- status parser
- diagnostics checks
- import/export helpers

## Metadata example

```python
BackendMetadata(
    id="openfortivpn",
    name="OpenFortiVPN",
    supports_password=True,
    supports_certificate_fingerprint=True,
)
```

## Future plugins

- OpenFortiVPN
- WireGuard
- OpenVPN
- OpenConnect
- StrongSwan

## Rule

The UI must not contain backend-specific branches unless strictly necessary for user-facing labels.
