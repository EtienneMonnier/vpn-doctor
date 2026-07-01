# ADR-0007 - No Real Secrets in Repository

## Status

Accepted

## Context

VPN projects can easily leak sensitive data through profiles, logs, screenshots and
examples.

## Decision

The repository must not contain real VPN endpoints, passwords, usernames, private
certificates, tokens or unredacted logs.

## Consequences

Examples must use placeholders. Real troubleshooting cases must be sanitized.
