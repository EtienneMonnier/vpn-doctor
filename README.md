# VPN Doctor

VPN Doctor is a Linux desktop assistant designed to diagnose, repair and document VPN connection issues.

It does not aim to replace NetworkManager. Instead, it helps users and administrators understand why a VPN profile fails, compares available backends, and suggests or applies safe corrections.

## Goals

- Diagnose VPN problems clearly.
- Work with NetworkManager when possible.
- Detect backend-specific issues.
- Compare NetworkManager plugins with direct CLI tools.
- Provide human-readable explanations.
- Generate support reports.
- Offer safe corrective actions.
- Integrate with GNOME and Linux desktops.

## Initial target

The first backend will focus on Fortinet SSL-VPN because `NetworkManager-fortisslvpn` can behave differently from `openfortivpn`.

The initial real-world case behind this project:

- FortiGate SSL-VPN on custom port `44443`.
- Self-signed FortiGate certificate.
- `openfortivpn` works.
- `NetworkManager-fortisslvpn` connects but traffic does not return.
- Manual `trusted-cert` addition is required.
- Split tunnel behavior must be checked.

## Project direction

VPN Doctor should be a diagnostic and repair assistant, not another generic VPN manager.

It should answer questions such as:

- Is the VPN gateway reachable?
- Is the certificate trusted?
- Is the tunnel really up?
- Are routes installed correctly?
- Is DNS configured correctly?
- Is traffic leaving the tunnel?
- Is traffic returning?
- Is the NetworkManager plugin failing while the CLI backend works?
- What should be fixed?
