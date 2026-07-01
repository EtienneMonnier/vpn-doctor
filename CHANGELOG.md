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

## Sprint 2.2

- Added OpenFortiVPN process manager components.
- Added backend registry and backend manager.
- Added log parser and connection state machine.
- Added safe CLI status and dry-run connect commands.



## Sprint 2.3

- Added real OpenFortiVPN CLI execution path.
- Added `connect --wait` and `--timeout`.
- Added environment-based temporary secret provider.
- Added JSON profile loading from user configuration.
- Added tests for settings, secrets and connection wait lifecycle.
