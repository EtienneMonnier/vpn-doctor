# ADR-0009 - Event Driven Backend Status

## Status

Proposed

## Context

The future UI needs live log and status updates.

## Decision

Backend status should eventually be exposed through events rather than direct UI polling.

## Consequences

The current simple event models may evolve into an event bus.
