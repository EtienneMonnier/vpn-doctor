# Diagnostics Guide

Diagnostics are the core of VPN Doctor.

## Diagnostic philosophy

A diagnostic must not only say "failed". It must explain what was checked and what
the user can do.

Each check should produce:

- name;
- success flag;
- message;
- suggestion;
- severity later.

## Initial checks

- VPN binary installed.
- Gateway reachable.
- Certificate fingerprint available.
- Tunnel interface exists.
- Routes installed.
- DNS servers received.
- Corporate host reachable.
- Internet still reachable if split tunnel is expected.

## Fortinet-specific checks

- Custom port present.
- Self-signed certificate detected.
- `trusted-cert` missing.
- NetworkManager profile differs from openfortivpn behavior.
- Tunnel up but no replies received.

## Report output

Reports should eventually be exportable as:

- Markdown;
- JSON;
- HTML.
