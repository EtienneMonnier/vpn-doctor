# ADR-0006 - CLI First During Early Sprints

## Status

Accepted

## Context

The GTK UI is planned, but backend and diagnostics logic must be stable before a GUI is
built on top.

## Decision

Early sprints use a CLI entry point.

## Consequences

- Faster testing.
- Easier CI.
- No GTK dependency in backend tests.
- The future GUI will reuse the same controller and services.
