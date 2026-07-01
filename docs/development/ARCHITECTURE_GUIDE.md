# Architecture Guide

## Why layered architecture?

VPN clients easily become fragile if UI code directly manipulates commands, routes, DNS, secrets, and logs.

VPN Doctor deliberately separates responsibilities:

- UI displays.
- Controllers coordinate.
- Services decide.
- Backends connect.
- Diagnostics explain.

## Dependency direction

Allowed:

```text
ui -> core
core -> services
services -> backend
services -> diagnostics
services -> models
backend -> models
diagnostics -> models
```

Forbidden:

```text
backend -> ui
diagnostics -> ui
models -> services
utils -> services
```

## Events and state

The application should eventually expose state changes as events.

Examples:

- `ConnectionStarted`
- `ConnectionAuthenticated`
- `TunnelUp`
- `TunnelDown`
- `DiagnosticCompleted`
- `CertificateMismatchDetected`

## Error model

Backend errors must be translated into structured errors.

Example:

```text
Raw error:
Gateway certificate validation failed.

Structured:
code: certificate_untrusted
severity: error
explanation: The VPN gateway uses a certificate that is not trusted locally.
suggested_fix: Store the certificate fingerprint if you trust this gateway.
```

## Profiles

A profile contains non-secret data:

- name
- backend
- gateway
- port
- username
- realm
- certificate fingerprint
- expected internal hosts
- expected DNS servers

A profile must not contain:

- password
- token
- private key

## Diagnostics pipeline

Before connection:

1. Validate profile.
2. Check backend availability.
3. Check gateway reachability.
4. Check certificate fingerprint if possible.

During connection:

1. Parse backend output.
2. Detect authentication failure.
3. Detect MFA/SAML if visible.
4. Detect tunnel-up event.

After connection:

1. Check interface.
2. Check routes.
3. Check DNS.
4. Check internal reachability.
5. Check Internet reachability.
6. Detect full tunnel or split tunnel.

## Future plugin architecture

A plugin should provide:

- backend metadata
- profile schema
- connect/disconnect implementation
- log parser
- diagnostics provider
- import/export helpers
