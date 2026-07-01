# Test Strategy

## Goals

Tests should verify behaviour without requiring a real VPN.

## Test types

### Unit tests

- models;
- command builders;
- log parsers;
- diagnostic item aggregation.

### Integration-style tests

Use mocked subprocesses and sanitized logs.

### Manual tests

Real VPN tests must be documented separately and must not require committing secrets.

## Commands

```bash
python -m pip install -e ".[dev]"
pytest
```

## Coverage priorities

High priority:

- secret safety;
- command construction;
- log parsing;
- diagnostic classification;
- status transitions.

Lower priority initially:

- GTK UI rendering;
- packaging.
