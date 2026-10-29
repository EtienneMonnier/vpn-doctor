# ADR-0011 - VPN Doctor as a NetworkManager Overlay

## Status

Accepted

## Context

Fedora and most desktop distributions manage VPNs with NetworkManager.
Connections, secrets (GNOME secret agent and keyring) and privileges already
work there. What users miss is feedback: GNOME reports most failures as
"activation failed", while the cause sits in the NetworkManager reason and in
the VPN plugin log in the journal. No existing tool explains them.

## Decision

- VPN Doctor drives existing NetworkManager connections; it does not create
  or edit them. GNOME Settings and nm-connection-editor remain the editors.
- The backend uses `nmcli` (stable, scriptable, no D-Bus main loop in the
  CLI) for discovery, activation and status.
- Secrets stay with the GNOME secret agent and the keyring. VPN Doctor never
  asks for or sees NetworkManager passwords.
- During a session, VPN Doctor follows the NetworkManager journal and keeps
  only the lines of the connection and of its VPN plugin.
- Failures are explained by rules matching the NetworkManager reason and the
  plugin log (`diagnostics/vpn_plugins.py`), the plugin cause first.
- The direct `openfortivpn` backend stays, as a fallback when
  NetworkManager-fortisslvpn fails (first case study), and for gateways that
  need options the plugin lacks.
- NetworkManager connections outlive the VPN Doctor window, like in GNOME
  Settings. Only tunnels VPN Doctor runs itself stop with the window.

## Consequences

- Multiple connections come for free from NetworkManager.
- The journal must be readable by the user (default on Fedora for wheel
  members). Without it, explanations fall back to the NetworkManager reason.
- WireGuard handshakes cannot be inspected without root; this is left to
  post-connection diagnostics.
