# Roadmap

VPN Doctor is developed in small, reviewable sprints.

## Version strategy

| Version | Meaning |
| --- | --- |
| `v0.0.x` | foundation, architecture and prototypes |
| `v0.1.x` | OpenFortiVPN MVP |
| `v0.2.x` | diagnostics engine |
| `v0.3.x` | profile management and secrets |
| `v0.4.x` | GTK4 / Libadwaita UI |
| `v0.5.x` | multiple backends |
| `v1.0.0` | first stable release |

## Sprint 0 - Foundation

Status: complete.

Delivered:

- repository structure;
- documentation foundation;
- branding direction;
- initial architecture;
- AGENTS.md;
- ADR structure.

## Sprint 1 - Core foundation

Status: complete.

Delivered:

- package structure;
- application bootstrap;
- CLI entry point;
- controller;
- models;
- OpenFortiVPN backend skeleton;
- basic diagnostics;
- first tests.

## Sprint 2 - OpenFortiVPN backend design and safe lifecycle

Status: in progress.

Goals:

- document backend lifecycle;
- define connection state machine;
- define log parsing strategy;
- define process management rules;
- add tests before real lifecycle implementation;
- keep secrets out of command line and logs.

Sprint 2 is intentionally careful. A VPN backend touches networking, subprocesses and
secrets. The implementation must be testable and easy to reason about.

## Sprint 3 - Diagnostics engine

Status: started. Sprint 3.1 delivered the Remote Desktop diagnostic.

Goals:

- global diagnostic result model;
- route checks;
- DNS checks;
- gateway checks;
- certificate checks;
- PPP interface checks;
- services behind the tunnel (RDP done; SMB, HTTP later);
- readable suggestions.

## Sprint 4 - NetworkManager overlay

Status: started. Sprint 4.1 delivered the NetworkManager backend (ADR-0011).
Profiles and secrets are delegated to NetworkManager and the GNOME keyring;
the items below now only concern direct backends such as openfortivpn.

Goals:

- profile storage format;
- Secret Service integration;
- import/export;
- safe sample profiles;
- validation rules.

## Sprint 5 - GTK4 / Libadwaita UI

Status: mostly delivered (dashboard layout, tabs, skins, preferences, logo,
startup animation). Remaining: diagnostic report view.

Goals:

- main window;
- profile selector;
- connect/disconnect;
- live logs;
- status pill;
- timer;
- diagnostic report view.

## Sprint 6 - Packaging

Status: RPM done (0.1.0); DEB planned; Flatpak postponed (see the packaging
guide).

Goals:

- Flatpak manifest;
- RPM packaging notes;
- DEB packaging notes;
- GitHub release assets.

## Backlog (next ideas)

### AI agents: JSON output, then an MCP server

1. Done in Sprint 7.1: `--json` on every CLI command, with a stable,
   documented schema. Useful for scripts and for any agent that can run a
   command.
2. `docs/AGENTS_USAGE.md`: how an agent diagnoses a VPN with VPN Doctor
   (commands, JSON fields, what each failure means, what never to do).
3. `vpn-doctor mcp`: a stdio MCP server, as an optional extra
   (`vpn-doctor[mcp]`) so the base package keeps no dependency.
   - Read-only tools first: profiles, status, diagnose, conflicts, explain a
     log, RDP probe.
   - Connect and disconnect only with explicit user confirmation.
   - Never expose secrets, nor raw logs containing user names or addresses.

### Background mode and tray

- Keep running in the background when the window closes while a VPN is
  connected, with desktop notifications for state changes (connected,
  dropped, conflict).
- GNOME 46+: use the Background portal (shown in Quick Settings). Other
  desktops and the AppIndicator extension: a StatusNotifierItem over D-Bus
  (GTK 4 has no tray icon API).
- Preference: "Reduce to the background when connected".

### Translations

- Fix `i18n.py`: it looks for translations in a relative `locale` folder;
  install `.mo` files under `/usr/share/locale` and bind the text domain.
- Extract strings with xgettext into `po/vpn-doctor.pot`; compile in the RPM.
- First languages: French, German, Spanish, Italian, Dutch, Portuguese,
  Polish.
- Diagnostic explanations are user-facing strings too: translate them.

## Later

- report export;
- automatic safe fixes;
- health score;
- DEB package; NetworkManager-only Flatpak.


## Sprint 2.4 - GTK/libadwaita UI skeleton

Status: implemented in feature pack.

Goals:
- Add experimental GUI entry point.
- Display current VPN status.
- Add Connect and Disconnect buttons.
- Add log area.
- Keep backend execution safe until UI wiring is implemented.


## Sprint 2.5 - UI integration

Status: implemented.

Delivered:
- Connect/Disconnect wired to the backend through the controller.
- Password dialog, live logs, connection timer, Diagnose button.
- pkexec privilege escalation (ADR-0010).
- Restored the unmerged Sprint 2.3 code.

Next:
- profile selector;
- single polkit authorization through a dedicated helper;
- validation against a real gateway.
