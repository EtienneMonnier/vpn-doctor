# Testing Guide

## Test levels

### Unit tests

- dataclasses;
- log parsers;
- command builders;
- diagnostic checks with mocks.

### Integration tests

- external binary detection;
- sample log parsing;
- fake backend process output.

### Manual tests

- real VPN connections;
- route inspection;
- DNS inspection;
- GUI behavior.

## Rule

Tests must not require a real VPN account.

Real VPN tests must be documented as manual procedures.
