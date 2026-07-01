# VPN Doctor

**Diagnose. Connect. Protect.**

VPN Doctor is a Linux VPN troubleshooting and connection assistant.

🛡️ VPN Doctor

Diagnose. Connect. Protect.

A modern Linux VPN troubleshooting and connection assistant.

Current Status

✔ Foundation completed
🚧 Sprint 1 in progress

Supported backends

✔ OpenFortiVPN
⏳ WireGuard
⏳ OpenVPN
⏳ OpenConnect

License

MIT

Foundation      ██████████ 100%
Core            ░░░░░░░░░░   0%
GUI             ░░░░░░░░░░   0%
Diagnostics     ░░░░░░░░░░   0%
Plugins         ░░░░░░░░░░   0%
Release 1.0     ░░░░░░░░░░   0%


It is not designed to replace NetworkManager. Its goal is to help users understand why a VPN connection fails, choose the best available backend, and apply safe fixes when possible.

## Project goals

- Provide a modern Linux desktop experience.
- Diagnose common VPN failures.
- Explain problems in plain language.
- Support multiple VPN backends over time.
- Start with OpenFortiVPN because it solves a real-world tested case.
- Integrate with GNOME Keyring / Secret Service for secrets.
- Use gettext for translations from the beginning.

## First MVP

The first version focuses on one working backend:

- OpenFortiVPN profile support
- Connect / disconnect
- Connection timer
- Live log viewer
- Basic diagnostics
- GNOME notifications
- Secure password handling

## Long-term vision

VPN Doctor should become a backend-independent Linux VPN assistant supporting OpenFortiVPN, WireGuard, OpenVPN, OpenConnect, and StrongSwan.

## Branding

Name: **VPN Doctor**

Tagline: **Diagnose. Connect. Protect.**

Visual direction: blue shield + stethoscope.

## Documentation

Start here:

1. [`ARCHITECTURE.md`](ARCHITECTURE.md)
2. [`ROADMAP.md`](ROADMAP.md)
3. [`AGENTS.md`](AGENTS.md)
4. [`docs/INDEX.md`](docs/INDEX.md)

