# Roadmap

## Sprint 0 - Foundation

Status: in progress.

Goals:

- Define vision.
- Define architecture.
- Document design rules.
- Establish branding.
- Prepare project structure.
- Prepare AI/contributor guidelines.
- Prepare first ADRs.

Deliverables:

- README
- AGENTS.md
- Architecture docs
- Development guides
- Branding guide
- Case study
- Roadmap

## Sprint 1 - Minimal OpenFortiVPN MVP

Goals:

- Load a local VPN profile.
- Connect using OpenFortiVPN.
- Disconnect cleanly.
- Show status.
- Show live logs.
- Show connection duration.
- Show desktop notifications.

Out of scope:

- Multiple backends.
- Advanced diagnostics.
- Auto-fixes.
- Packaging.

## Sprint 2 - Secure profiles

Goals:

- Store non-secret profile data in config files.
- Store secrets in GNOME Keyring / Secret Service.
- Add profile creation/editing UI.
- Add certificate fingerprint management.
- Add import/export without secrets.

## Sprint 3 - Diagnostics MVP

Goals:

- Gateway reachability check.
- Certificate trust check.
- Backend availability check.
- DNS status check.
- Route status check.
- Corporate reachability check.
- Markdown diagnostic report export.

## Sprint 4 - NetworkManager analysis

Goals:

- Detect existing NetworkManager VPN profiles.
- Inspect VPN plugin availability.
- Detect full-tunnel vs split-tunnel.
- Compare NetworkManager and CLI backend behavior.
- Suggest fallback to CLI backend when useful.

## Sprint 5 - Packaging

Goals:

- RPM package for Fedora.
- Flatpak prototype.
- Desktop launcher.
- AppStream metadata.
- Icons.

## Sprint 6 - Additional backends

Candidate order:

1. WireGuard
2. OpenVPN
3. OpenConnect
4. StrongSwan

## v1.0 criteria

VPN Doctor can be considered 1.0 when:

- OpenFortiVPN backend is stable.
- Profiles are manageable from the UI.
- Secrets are secure.
- Diagnostics are useful.
- Packaging is available.
- Documentation is complete.
- Basic translations are ready.
