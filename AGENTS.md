# AGENTS.md

This file is the development constitution for VPN Doctor.

It is intended for AI coding agents and human contributors.

## Mandatory reading order

Before making changes, read:

1. `README.md`
2. `ARCHITECTURE.md`
3. `ROADMAP.md`
4. `docs/INDEX.md`
5. Relevant files under `docs/development/`
6. Relevant ADRs under `docs/adr/`

## Project identity

Name:

```text
VPN Doctor
```

Tagline:

```text
Diagnose. Connect. Protect.
```

Mission:

```text
VPN Doctor helps Linux users diagnose, understand, and fix VPN problems.
```

VPN Doctor is not a NetworkManager replacement. It complements existing Linux VPN tools.

## Non-negotiable rules

- The GUI must never call VPN binaries directly.
- User-facing strings must use gettext.
- Passwords must never be committed, logged, or stored in plain text.
- Backends must use a common interface.
- Diagnostics must return structured results.
- Documentation must be updated when architecture changes.
- Prefer clear code over clever code.

## Architecture rule

Use this flow:

```text
UI
 ↓
Controller
 ↓
Service
 ↓
Backend / Diagnostics
 ↓
Operating System
```

## Coding style

- Python 3.12+ target.
- Type hints are required for new code.
- Use dataclasses for plain data structures.
- Use Python logging, not `print()`, except for temporary CLI smoke tests.
- Keep files focused.
- Keep functions small.
- Keep classes cohesive.

## Internationalization

English is the source language.

All user-visible strings:

```python
_("Connected")
```

Never:

```python
"Connected"
```

## Security

Never store:

- VPN passwords
- MFA tokens
- private keys
- private certificates
- customer-specific production data

Use:

- GNOME Keyring / Secret Service
- masked logs
- sanitized examples

## Documentation rules

Every feature should have one of:

- README section
- development guide update
- ADR if architectural
- user guide if user-visible

## Git rules

Branches:

```text
main
dev
feature/<name>
bugfix/<name>
hotfix/<name>
```

Commit examples:

```text
feat: add OpenFortiVPN backend
fix: detect untrusted FortiGate certificate
docs: expand diagnostics guide
refactor: split profile service
test: add route parser tests
```

## AI-specific instructions

When using Codex or any other coding agent:

1. Ask it to read `AGENTS.md`.
2. Ask it to inspect the current tree before editing.
3. Ask it to produce small commits.
4. Ask it not to introduce new dependencies without justification.
5. Ask it to update docs when behavior changes.
6. Ask it to avoid storing secrets in examples.

## Current priority

Sprint 0 and Sprint 1.

Do not implement WireGuard, OpenVPN or OpenConnect until the OpenFortiVPN MVP is clean.
