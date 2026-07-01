"""Internal event definitions for VPN Doctor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Event:
    """Base event."""

    name: str
    created_at: datetime


@dataclass(frozen=True)
class LogEvent(Event):
    """Event emitted when a backend produces a log line."""

    message: str
    level: str = "INFO"


@dataclass(frozen=True)
class StatusChangedEvent(Event):
    """Event emitted when VPN status changes."""

    status: str
