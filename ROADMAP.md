# Roadmap

## v0.1 - Fortinet diagnostic prototype

- GTK/libadwaita application skeleton.
- Fortinet SSL-VPN profile input.
- Gateway reachability test.
- Certificate fingerprint extraction.
- `trusted-cert` recommendation.
- NetworkManager profile inspection.
- `openfortivpn` test mode.
- Basic route, DNS and tunnel checks.
- Exportable diagnostic report.

## v0.2 - Guided repair

- Add missing `trusted-cert` to NetworkManager profiles.
- Detect wrong custom port configuration.
- Detect full tunnel versus split tunnel.
- Suggest `ipv4.never-default yes` when appropriate.
- Detect DNS suffix issues.
- Offer safe command preview before applying changes.

## v0.3 - Traffic analysis

- Run controlled ping tests.
- Capture traffic on VPN interface.
- Detect packets leaving without replies.
- Compare NetworkManager and CLI backend behavior.
- Detect possible MTU/MRU problems.

## v0.4 - Multi-backend framework

- Backend abstraction layer.
- Fortinet backend using `openfortivpn`.
- NetworkManager backend inspection.
- OpenConnect detection.
- OpenVPN detection.
- WireGuard detection.

## v0.5 - Desktop integration

- GNOME notifications.
- System tray or background status where available.
- Secure secret storage through GNOME Keyring / Secret Service.
- Application launcher.
- Light/dark theme support.

## v1.0 - Stable release

- RPM package for Fedora.
- Flatpak packaging study.
- Documentation.
- Translation support.
- Stable diagnostic reports.
- Safe repair mode.
