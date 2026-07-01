# Project Structure

## Current structure

```text
vpn-doctor/
├── .github/
├── assets/
├── docs/
├── examples/
├── packaging/
├── po/
├── src/
│   └── vpn_doctor/
│       ├── backend/
│       ├── core/
│       ├── diagnostics/
│       ├── models/
│       ├── services/
│       ├── ui/
│       ├── utils/
│       ├── app.py
│       └── i18n.py
├── tests/
├── AGENTS.md
├── ARCHITECTURE.md
├── README.md
├── ROADMAP.md
└── pyproject.toml
```

## Folder responsibilities

### `src/vpn_doctor/ui`

GTK4 / Libadwaita widgets and windows.

No subprocesses. No direct VPN logic.

### `src/vpn_doctor/core`

Application orchestration.

Controllers live here.

### `src/vpn_doctor/services`

Business logic services.

Examples:

- Profile service
- Secret service
- Connection service
- Notification service

### `src/vpn_doctor/backend`

VPN engine integrations.

Examples:

- OpenFortiVPN
- WireGuard
- OpenVPN
- OpenConnect

### `src/vpn_doctor/diagnostics`

Diagnostic checks and diagnostic engine.

### `src/vpn_doctor/models`

Dataclasses, enums and typed models.

### `src/vpn_doctor/utils`

Small helpers with no business logic.

### `docs`

Project documentation.

### `docs/adr`

Architecture Decision Records.

### `po`

Translations.

### `packaging`

Packaging files for RPM, Flatpak and DEB.

### `examples`

Example profiles and sanitized logs.
