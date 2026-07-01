# ADR: Layered architecture

## Status

Accepted

## Context

VPN Doctor needs stable foundations before implementation.

## Decision

The GUI must remain independent from VPN binaries and backend implementation details.

## Consequences

- The project remains easier to maintain.
- AI agents receive clear boundaries.
- Future contributors can understand why the choice was made.
