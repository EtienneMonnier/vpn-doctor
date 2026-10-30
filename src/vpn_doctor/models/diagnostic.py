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

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "success": self.success,
            "severity": str(self.severity),
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass(frozen=True)
class DiagnosticReport:
    """Collection of diagnostic results."""

    summary: str
    success: bool
    items: list[DiagnosticItem]

    @classmethod
    def from_items(cls, summary: str, items: list[DiagnosticItem]) -> DiagnosticReport:
        return cls(
            summary=summary,
            success=all(item.success for item in items),
            items=items,
        )

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "success": self.success,
            "items": [item.to_dict() for item in self.items],
        }
