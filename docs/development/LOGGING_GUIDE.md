# Logging Guide

## Rules

Use Python `logging`.

Do not use `print()` except for CLI user output.

## Log levels

- `DEBUG`: developer details;
- `INFO`: normal lifecycle;
- `WARNING`: suspicious but non-blocking;
- `ERROR`: failed action.

## Redaction

Before logging any backend line, ensure secrets are not present.

Future implementation should include a redaction utility.
