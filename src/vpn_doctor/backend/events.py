"""Backend event models.

Backend events are intentionally small immutable objects. They are used by
CLI code today and will later be consumed by the GTK UI without coupling the UI
to VPN-specific process handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC


@dataclass(frozen=True)
class BackendEvent:
    """Base backend event."""

    kind: str
    message: str
    created_at: datetime

    @classmethod
    def create(cls, kind: str, message: str) -> "BackendEvent":
        return cls(kind=kind, message=message, created_at=datetime.now(UTC))


@dataclass(frozen=True)
class BackendLogEvent(BackendEvent):
    """Event produced from a backend log line."""

    level: str = "INFO"
