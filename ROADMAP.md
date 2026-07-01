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

Goals:

- global diagnostic result model;
- route checks;
- DNS checks;
- gateway checks;
- certificate checks;
- PPP interface checks;
- readable suggestions.

## Sprint 4 - Profile and secret management

Goals:

- profile storage format;
- Secret Service integration;
- import/export;
- safe sample profiles;
- validation rules.

## Sprint 5 - GTK4 / Libadwaita UI

Goals:

- main window;
- profile selector;
- connect/disconnect;
- live logs;
- status pill;
- timer;
- diagnostic report view.

## Sprint 6 - Packaging

Goals:

- Flatpak manifest;
- RPM packaging notes;
- DEB packaging notes;
- GitHub release assets.

## Later

- NetworkManager inspection;
- WireGuard backend;
- OpenVPN backend;
- OpenConnect backend;
- report export;
- automatic safe fixes;
- health score.


## Sprint 2.3 - Real OpenFortiVPN CLI execution

Status: implemented in feature pack.

Goals:
- Start OpenFortiVPN from the CLI.
- Forward logs in real time.
- Wait for connected / failed / timeout.
- Load local profiles from the user config directory.
- Keep secrets outside the repository.
