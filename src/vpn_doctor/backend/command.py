"""Backend command models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BackendCommand:
    """Safe command representation.

    Passwords and secrets must never be stored in this object.
    """

    argv: list[str]
