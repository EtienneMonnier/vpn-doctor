# VPN Doctor

**Diagnose. Connect. Protect.**

VPN Doctor is a Linux VPN troubleshooting and connection assistant. It is not intended
to replace NetworkManager, WireGuard, OpenVPN, OpenConnect or OpenFortiVPN. Its role is
to help users and administrators understand what happens when a VPN works, partially
works, or fails.

VPN Doctor should eventually be able to:

- connect through supported VPN backends;
- compare backend behaviour;
- explain common VPN failures;
- produce readable diagnostic reports;
- suggest safe fixes;
- integrate cleanly with the Linux desktop.

## Current status

VPN Doctor is in early development.

| Area | Status |
| --- | --- |
| Project foundation | Done |
| Core Python structure | Done |
| OpenFortiVPN backend skeleton | Done |
| Sprint 2 backend design | Ready |
| Real OpenFortiVPN process lifecycle | Planned |
| GTK4 / Libadwaita UI | Planned |
| Diagnostics engine | Planned |
| Packaging | Planned |

## First backend

The first target backend is **OpenFortiVPN**.

This choice comes from a real-world FortiGate case where:

- `openfortivpn` connected successfully;
- `NetworkManager-fortisslvpn` established a PPP tunnel but did not pass useful traffic;
- certificate trust, split tunnel, DNS and routing required manual investigation.

That case became the first case study for the project.

## Design philosophy

VPN Doctor should not merely say "VPN failed".

It should say things like:

- "The gateway is reachable, but the certificate is not trusted."
- "The tunnel is up, but no replies return through PPP."
- "DNS was pushed by the VPN, but the search domain is missing."
- "NetworkManager failed, but OpenFortiVPN works with the same gateway."

## Quick development test

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
vpn-doctor --version
vpn-doctor profiles
vpn-doctor diagnose
pytest
```

The default profile is intentionally a safe placeholder and does not contain real VPN
data.

## Documentation map

Start here:

- [Architecture](ARCHITECTURE.md)
- [Roadmap](ROADMAP.md)
- [Documentation index](docs/INDEX.md)
- [Master architecture guide](docs/development/MASTER_ARCHITECTURE.md)
- [Sprint 2 specification](docs/development/SPRINT2_SPECIFICATION.md)
- [OpenFortiVPN backend specification](docs/development/OPENFORTIVPN_BACKEND_SPEC.md)
- [Diagnostics engine specification](docs/development/DIAGNOSTICS_ENGINE_SPEC.md)

## Security stance

VPN Doctor must never commit or expose real customer VPN data. Passwords, tokens and
private certificates must not be stored in source code, profile files, examples or logs.

Future secret storage will use the Linux Secret Service API through GNOME Keyring or a
compatible backend.


## Current development status

- Foundation documentation: completed
- Core CLI: completed
- OpenFortiVPN process manager: completed
- OpenFortiVPN real CLI execution path: in progress / Sprint 2.3
- GTK/libadwaita UI: planned

