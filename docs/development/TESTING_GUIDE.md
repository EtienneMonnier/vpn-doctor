# Testing Guide

## Goals

VPN Doctor must be reliable because VPN failures are already frustrating.

## Test levels

### Unit tests

For:

- parsers
- models
- services
- diagnostic result formatting

### Integration tests

For:

- backend process handling with mocked commands
- route parsing
- DNS parsing
- log parsing

### Manual tests

For:

- real OpenFortiVPN profile
- GNOME notifications
- keyring integration
- GTK UI behavior

## Mocking

Never require a real corporate VPN in CI.

Use sanitized log samples in:

```text
examples/logs/
```

## CI

GitHub Actions should run:

- import smoke test
- unit tests
- linting later
