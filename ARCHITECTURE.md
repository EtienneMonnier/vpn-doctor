# VPN Doctor Architecture

## Purpose

This document defines the global architecture of VPN Doctor.

VPN Doctor must remain modular. The GUI must not know how OpenFortiVPN, WireGuard or OpenVPN work internally. The UI asks application services to perform actions, and services delegate to backends and diagnostics providers.

## High-level flow

```text
User Interface
     ↓
Application Controller
     ↓
Services
     ↓
Diagnostics Engine
     ↓
Backend Interface
     ↓
Backend Implementations
     ↓
Linux System
```

## Main layers

### UI layer

Location:

```text
src/vpn_doctor/ui/
```

Responsibilities:

- Display profiles.
- Display connection state.
- Display logs.
- Display diagnostics results.
- Trigger user actions.
- Show notifications and toasts.

Forbidden:

- Direct subprocess calls.
- Direct calls to `openfortivpn`, `wg`, `openvpn`, `ip`, `nmcli`.
- Direct password storage.
- Direct route manipulation.

### Controller layer

Location:

```text
src/vpn_doctor/core/
```

Responsibilities:

- Coordinate user actions.
- Call services.
- Convert service state to UI-friendly state.
- Keep UI logic thin.

### Services layer

Location:

```text
src/vpn_doctor/services/
```

Core services:

- `ProfileService`
- `ConnectionService`
- `DiagnosticsService`
- `SecretService`
- `NotificationService`
- `SettingsService`
- `LogService`

### Backend layer

Location:

```text
src/vpn_doctor/backend/
```

Responsibilities:

- Implement VPN-specific logic.
- Run the underlying tool safely.
- Parse backend output.
- Report status changes.
- Never expose raw secrets.

Initial backend:

- OpenFortiVPN

Future backends:

- WireGuard
- OpenVPN
- OpenConnect
- StrongSwan

### Diagnostics layer

Location:

```text
src/vpn_doctor/diagnostics/
```

Responsibilities:

- Run diagnostic checks.
- Produce structured results.
- Suggest safe fixes.
- Explain failures in human-readable language.

### Models layer

Location:

```text
src/vpn_doctor/models/
```

Core models:

- `VPNProfile`
- `BackendType`
- `ConnectionStatus`
- `DiagnosticResult`
- `DiagnosticSeverity`
- `CertificateFingerprint`
- `RouteInfo`
- `DnsInfo`

## Dependency rules

Allowed direction:

```text
ui -> core -> services -> backend/diagnostics/models/utils
```

Not allowed:

```text
backend -> ui
diagnostics -> ui
models -> services
utils -> services
```

## Error handling

Every technical error should be mapped to a user-facing explanation when possible.

Bad:

```text
Process exited with code 1
```

Better:

```text
The VPN gateway certificate is not trusted.
VPN Doctor can store this fingerprint if you trust this gateway.
```

## Internationalization

All user-facing strings must go through gettext.

See:

```text
docs/development/I18N_GUIDE.md
```

## Security

Secrets must never be stored in profile files.

Use Secret Service / GNOME Keyring.

See:

```text
docs/development/SECURITY_GUIDE.md
```
