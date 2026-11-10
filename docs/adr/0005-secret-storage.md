# ADR 0005 - Secret Storage

## Status

Accepted. Implemented in Sprint 4.2.

## Decision

Long-term secrets will be stored through Secret Service / GNOME Keyring.

## Rationale

VPN passwords must not be stored in plain text or command-line history.

## Implementation notes

- VPN Doctor uses libsecret, not a GNOME-specific API, so any Secret Service
  provider works: GNOME Keyring, KDE Wallet (through ksecretd), KeePassXC.
- NetworkManager connections keep their own secret flow (GNOME secret agent).
- One-time codes are never stored.
