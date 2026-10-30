# Sprint 7.1 Implementation Report

## Summary

Every CLI command except `gui` accepts `--json`. This is the first step of
the "AI agents" backlog item: any script or agent that can run a command can
now read VPN Doctor's diagnosis without parsing text.

## Specification

- `--json` is accepted before or after the command.
- One JSON object on stdout, same exit codes as the text output.
- Errors become `{"error": ...}`; `connect` returns the backend log in the
  result instead of streaming it.
- Never secrets, user names or certificate paths.
- Schema: `docs/development/CLI_SPECIFICATION.md`.

## Implementation

- `to_dict()` on `DiagnosticItem`, `DiagnosticReport`, `VPNStatus` and
  `VPNProfile`: explicit field lists, so a new model field never leaks into
  the output by accident.
- `ApplicationController.run()`: a `json_option` parent parser with
  `default=argparse.SUPPRESS`, so the subcommand flag does not reset the
  global one; small `_output`, `_result`, `_error` helpers.
- `rdp --log` with an unreadable file now exits with code 2 instead of a
  traceback.

## Validation

```bash
ruff check src tests
pytest            # 167 passed
```

`profiles`, `status` and `conflicts --json` were also run against the
developer's real NetworkManager connections.

## Review notes

- `ruff` was missing from the development virtualenv although listed in the
  `dev` extra; it is installed with `pip install -e ".[dev]"`.
- `ruff format` is not applied to the repository; only `ruff check` is.
- Next: `docs/AGENTS_USAGE.md`, then an optional MCP server, then
  translations.
