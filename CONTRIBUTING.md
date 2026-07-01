# Contributing

VPN Doctor is early-stage.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

## Checks

```bash
vpn-doctor --version
vpn-doctor profiles
vpn-doctor diagnose
pytest
```

## Rules

- Do not commit secrets.
- Do not commit real customer VPN details.
- Keep `main` stable.
- Work on `dev` or feature branches.
- Update docs when architecture changes.

## Commit style

Use conventional commits.

Examples:

```text
feat: add OpenFortiVPN backend lifecycle
fix: handle missing openfortivpn binary
docs: document backend state machine
test: add diagnostics model tests
```
