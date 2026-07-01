# Packaging Guide

## Targets

- Flatpak
- RPM
- DEB

## Flatpak

Flatpak is the preferred desktop distribution target.

Challenges:

- VPN tools may need host access;
- `openfortivpn` may not be available inside sandbox;
- integration with Secret Service and NetworkManager must be designed carefully.

## RPM

Fedora is the reference development platform.

## DEB

Ubuntu and Debian should be supported after the MVP stabilizes.
