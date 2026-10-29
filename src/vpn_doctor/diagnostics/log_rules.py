"""Explain known messages found in third-party logs.

A rule maps marker substrings to a human explanation. Raw log lines are never
copied into the result: they contain host names, usernames and addresses.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from vpn_doctor.models.diagnostic import DiagnosticItem, DiagnosticSeverity


@dataclass(frozen=True)
class LogRule:
    """One known log message and what it means."""

    markers: tuple[str, ...]
    name: str
    message: str
    suggestion: str | None
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR

    def matches(self, line: str) -> bool:
        return any(marker in line for marker in self.markers)

    def to_item(self) -> DiagnosticItem:
        return DiagnosticItem(
            name=self.name,
            success=self.severity == DiagnosticSeverity.INFO,
            message=self.message,
            suggestion=self.suggestion,
            severity=self.severity,
        )


def match_rules(lines: Iterable[str], rules: Sequence[LogRule]) -> list[LogRule]:
    """Return the rules matched by the lines, in rule order (most specific first)."""
    matched: set[LogRule] = set()
    for line in lines:
        for rule in rules:
            if rule not in matched and rule.matches(line):
                matched.add(rule)
    return [rule for rule in rules if rule in matched]
