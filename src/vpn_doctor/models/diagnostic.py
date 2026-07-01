"""Diagnostic result models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DiagnosticSeverity(StrEnum):
    """Severity of a diagnostic item."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class DiagnosticItem:
    """Single diagnostic check result."""

    name: str
    success: bool
    message: str
    suggestion: str | None = None
    severity: DiagnosticSeverity = DiagnosticSeverity.INFO


@dataclass(frozen=True)
class DiagnosticReport:
    """Collection of diagnostic results."""

    summary: str
    success: bool
    items: list[DiagnosticItem]

    @classmethod
    def from_items(cls, summary: str, items: list[DiagnosticItem]) -> "DiagnosticReport":
        return cls(
            summary=summary,
            success=all(item.success for item in items),
            items=items,
        )
