# ADR: Use Secret Service

## Status

Accepted

## Context

VPN Doctor needs stable foundations before implementation.

## Decision

Secrets must be stored through GNOME Keyring / Secret Service, not profile files.

## Consequences

- The project remains easier to maintain.
- AI agents receive clear boundaries.
- Future contributors can understand why the choice was made.
