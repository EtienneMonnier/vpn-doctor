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

## Sprint 3.1

### Added

- `vpn-doctor rdp` to diagnose a Remote Desktop server behind the VPN, with
  FreeRDP/Remmina log explanations.
- Client certificate support in profiles (`user_cert`, `user_key`).
- Case study: RDP licensing failure behind a working WireGuard tunnel.

### Fixed

- The GUI hung on "VPN account password:" when the gateway asked a further
  question: prompts printed without a newline (two-factor token) were never
  shown. They now open a dialog and the answer is sent to openfortivpn.
- openfortivpn logs arrived late or never: its output is now line-buffered
  through `stdbuf`.
- Tests no longer read the developer's real `~/.config/vpn-doctor` profiles.

## Sprint 4.1

### Added

- NetworkManager overlay: discover, connect and disconnect VPN and WireGuard
  connections, with failures explained from the NetworkManager reason and
  the VPN plugin log (ADR-0011).
- `--profile NAME` for `connect`, `disconnect`, `status` and `diagnose`.
- Redesigned GTK UI with a connection selector.
- Custom skins (GTK CSS) with live reload, and the "Wasteland Terminal" skin.
