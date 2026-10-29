# Changelog

## Unreleased

### Added

- Sprint 2 architecture review pack.
- Master architecture documentation.
- OpenFortiVPN backend specification.
- Diagnostics engine specification.
- Backend state machine documentation.
- Event system documentation.
- Plugin system documentation.
- Test strategy documentation.
- Additional ADRs.
- Repository review report.

### Changed

- Clarified that VPN Doctor is a diagnostics-first assistant, not a NetworkManager replacement.
- Strengthened security and sanitization guidelines.
- Expanded roadmap and sprint structure.

## v0.0.1-foundation

### Added

- Initial repository structure.
- Documentation foundation.
- Project identity.
- GitHub workflow and contribution files.


## Sprint 2.4

- Added experimental GTK4/libadwaita UI skeleton.
- Added `vpn-doctor gui` and `vpn-doctor-gui`.
- Added UI view models and tests.
- Updated README and roadmap with GUI progress.


## Sprint 2.5

### Fixed

- Restored Sprint 2.3 profile loading and `connect --wait`, which were never
  merged and made `vpn-doctor profiles` crash.
- Recognized real openfortivpn 1.23 failure messages (wrong password, root
  privileges, unreachable gateway) and kept the `failed` state after them.
- Fixed log lines joined by a literal `\n` in the GUI.

### Added

- Readable failure suggestions in the CLI and the GUI.
- `pkexec` privilege escalation and `-c /dev/null` configuration isolation
  (ADR-0010).
- Profiles from `~/.config/vpn-doctor/profiles.json`, rejecting secrets.
- GUI connect/disconnect, password dialog, live logs, timer and Diagnose button.

### Removed

- Accidental nested `vpn-doctor/` copy of the repository.
