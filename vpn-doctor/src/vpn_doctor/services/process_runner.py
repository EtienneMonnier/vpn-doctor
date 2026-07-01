"""Safe subprocess helpers for VPN Doctor.

The process runner is deliberately small and injectable so backends can be tested
without launching real VPN clients.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol, TextIO


@dataclass(frozen=True)
class ProcessStartResult:
    """Information about a started subprocess."""

    pid: int
    argv: list[str]


class ManagedProcess(Protocol):
    """Protocol implemented by subprocess-like objects."""

    pid: int
    stdout: TextIO | None

    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...

    def wait(self, timeout: float | None = None) -> int: ...


class ProcessRunner:
    """Start long-running commands.

    This class is the only low-level place where `subprocess.Popen` should be used.
    Backends receive a runner instance, which makes process execution mockable.
    """

    def start(self, argv: Iterable[str], stdin_text: str | None = None) -> ManagedProcess:
        process = subprocess.Popen(
            list(argv),
            stdin=subprocess.PIPE if stdin_text is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        if stdin_text is not None and process.stdin is not None:
            process.stdin.write(stdin_text)
            process.stdin.flush()
            process.stdin.close()

        return process
