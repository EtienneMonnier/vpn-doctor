# ADR-0008 - Safe OpenFortiVPN Lifecycle

## Status

Accepted

## Context

`openfortivpn` requires subprocess management and may require secrets through stdin.

## Decision

Sprint 2 will design and test process lifecycle carefully before adding a polished UI.

## Consequences

The backend must avoid `shell=True`, avoid passwords in argv and support clean
termination.
