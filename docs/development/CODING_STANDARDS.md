# Coding Standards

## Python

Target Python:

```text
Python 3.12+
```

Minimum currently declared in `pyproject.toml` may remain lower during bootstrap, but new code should be compatible with 3.12+.

## Style

- PEP 8
- Type hints
- Small functions
- Cohesive classes
- Dataclasses for structured data
- Enums for fixed state

## Line length

```text
100
```

## Logging

Use:

```python
import logging

logger = logging.getLogger(__name__)
logger.info("Starting backend")
```

Avoid:

```python
print("Starting backend")
```

## Exceptions

Raise specific exceptions.

Bad:

```python
raise Exception("failed")
```

Better:

```python
raise BackendConnectionError("Gateway unreachable")
```

## Subprocess

Subprocess calls must be isolated in backend or system utility modules.

Rules:

- Never pass secrets through command-line arguments.
- Prefer stdin or keyring retrieval.
- Capture output carefully.
- Redact secrets before logging.

## Naming

- Python package: `vpn_doctor`
- Repository: `vpn-doctor`
- Class names: `OpenFortiVPNBackend`
- Service names: `ProfileService`
- Diagnostic names: `GatewayReachabilityCheck`

## Configuration

Configuration should eventually use:

```text
~/.config/vpn-doctor/
```

Secrets:

```text
Secret Service / GNOME Keyring
```
