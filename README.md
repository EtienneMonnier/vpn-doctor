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
| Sprint 2 backend design | Done |
| Real OpenFortiVPN process lifecycle | Experimental |
| GTK4 / Libadwaita UI | Experimental |
| Diagnostics engine | Started (RDP) |
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


## NetworkManager connections

VPN Doctor is a companion to NetworkManager, not a replacement. It lists the
VPN and WireGuard connections you already created in GNOME Settings, connects
them, shows the plugin log live and explains failures that GNOME only reports
as "activation failed". Passwords stay with the GNOME keyring.

```bash
vpn-doctor profiles
vpn-doctor connect --profile "Office VPN" --wait
```

## Direct openfortivpn profiles

For gateways where NetworkManager-fortisslvpn fails, VPN Doctor can also run
`openfortivpn` itself. It reads these profiles from `~/.config/vpn-doctor/profiles.json`. Without
that file it shows a safe demo profile. Passwords are never stored there.

```json
{
  "profiles": [
    {
      "name": "Office",
      "backend": "openfortivpn",
      "host": "vpn.example.com",
      "port": 443,
      "username": "demo-user",
      "trusted_cert": "abcdef...",
      "user_cert": "/etc/openfortivpn/demo-cert.pem",
      "user_key": "/etc/openfortivpn/demo-key.pem"
    }
  ]
}
```

`user_cert` and `user_key` are optional paths to a client certificate and its
key. Keep these files readable by root only.

## Remote Desktop behind the VPN

When the tunnel is up but a Windows server refuses the session:

```bash
journalctl --user -b -o cat | vpn-doctor rdp 192.0.2.41 --log -
```

VPN Doctor tests the port, the RDP negotiation and TLS without sending any
credentials, then explains FreeRDP/Remmina errors such as expired licensing,
expired passwords or missing Remote Desktop permissions. See the
[case study](docs/case-studies/rdp-licensing-behind-wireguard.md).

## Experimental GUI

The window shows the selected connection, its status and timer, live logs and
a Diagnose button. Use the **SKIN** menu to change its look, or write your own
skin in CSS: see [Skins](docs/development/THEMES.md).

Run:

```bash
vpn-doctor gui
```

or:

```bash
vpn-doctor-gui
```

For direct openfortivpn profiles, Connect asks for the VPN password, which is
passed to `openfortivpn` through stdin and never stored.

`openfortivpn` needs root privileges. VPN Doctor stays unprivileged and starts
it through `pkexec`, so polkit asks for administrator authentication (see
[ADR-0010](docs/adr/0010-pkexec-privilege-escalation.md)).
