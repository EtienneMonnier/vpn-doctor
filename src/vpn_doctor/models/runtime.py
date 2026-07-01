"""Runtime options for VPN operations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectOptions:
    """Options used when starting a backend connection."""

    dry_run: bool = False
    wait: bool = False
    timeout_seconds: float = 60.0
