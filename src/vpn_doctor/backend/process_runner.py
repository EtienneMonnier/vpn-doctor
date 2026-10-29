"""Generic process runner used by VPN backends."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from vpn_doctor.backend.errors import BackendAlreadyRunningError, BackendProcessError

LOGGER = logging.getLogger(__name__)

LineCallback = Callable[[str], None]

# Interactive prompts are printed without a trailing newline, e.g.
# "Two-factor authentication token: ". They must be surfaced immediately.
PROMPT_SUFFIX = ": "


def line_buffering_command() -> tuple[str, ...]:
    """Return a prefix that makes a C program flush its output at each line.

    Programs writing to a pipe buffer their output in blocks, so logs would
    only arrive once several kilobytes are pending, or at exit.
    """
    if shutil.which("stdbuf"):
        return ("stdbuf", "-oL", "-eL")
    return ()


@dataclass
class ProcessRunner:
    """Thin wrapper around subprocess.Popen.

    It keeps process handling outside backend business logic and makes tests
    easier to write.
    """

    process: subprocess.Popen[str] | None = None
    _reader_thread: threading.Thread | None = field(default=None, init=False, repr=False)

    def start(
        self,
        command: Sequence[str],
        on_line: LineCallback | None = None,
        stdin_text: str | None = None,
        on_prompt: LineCallback | None = None,
    ) -> None:
        if self.is_running:
            raise BackendAlreadyRunningError("A backend process is already running")

        try:
            self.process = subprocess.Popen(
                list(command),
                stdin=subprocess.PIPE if stdin_text is not None else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            raise BackendProcessError(str(exc)) from exc

        if stdin_text is not None and self.process.stdin is not None:
            self.process.stdin.write(stdin_text)
            self.process.stdin.flush()

        if on_line is not None and self.process.stdout is not None:
            self._reader_thread = threading.Thread(
                target=self._read_output,
                # Pass the stream itself: holding it keeps the descriptor open
                # even after terminate() drops the Popen object.
                args=(self.process.stdout, on_line, on_prompt or on_line),
                daemon=True,
            )
            self._reader_thread.start()

    def write_stdin(self, text: str) -> None:
        """Send text to a running process, e.g. the answer to a prompt."""
        if not self.is_running or self.process.stdin is None:
            raise BackendProcessError("The backend process does not accept input")
        self.process.stdin.write(text)
        self.process.stdin.flush()

    @staticmethod
    def _read_output(stream, on_line: LineCallback, on_prompt: LineCallback) -> None:
        # Read raw chunks instead of iterating lines: a prompt has no newline
        # and would otherwise stay invisible while the process waits for it.
        pending = ""
        while chunk := ProcessRunner._read_chunk(stream):
            pending += chunk.decode("utf-8", errors="replace")
            *lines, pending = pending.split("\n")
            for line in lines:
                on_line(line.rstrip("\r"))
            if pending.endswith(PROMPT_SUFFIX):
                on_prompt(pending)
                pending = ""
        if pending:
            on_line(pending)

    @staticmethod
    def _read_chunk(stream) -> bytes:
        try:
            return os.read(stream.fileno(), 4096)
        except (OSError, ValueError):  # stream closed while the process stops
            return b""

    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def terminate(
        self,
        timeout: float = 5.0,
        privilege_command: Sequence[str] = (),
        close_stdin_first: bool = False,
    ) -> None:
        """Stop the process.

        With close_stdin_first, closing stdin is the stop request (the
        privileged helper stops openfortivpn when its stdin closes); signals
        are only a fallback.

        A process started through pkexec runs as root once pkexec has replaced
        itself, so the current user may not signal it. In that case the
        signal is sent through the same privilege command.
        """
        if self.process is None:
            return

        if close_stdin_first and self.is_running and self.process.stdin is not None:
            try:
                self.process.stdin.close()
                self.process.wait(timeout=timeout)
            except (OSError, subprocess.TimeoutExpired):
                LOGGER.warning("The process did not stop when its stdin closed")

        if not self.is_running:
            self.process = None
            return

        try:
            self.process.terminate()
        except PermissionError:
            if not privilege_command:
                raise
            LOGGER.info("Stopping privileged process %s through %s", self.process.pid, privilege_command[0])
            subprocess.run(
                [*privilege_command, "kill", "-TERM", str(self.process.pid)],
                check=False,
                stdin=subprocess.DEVNULL,
            )

        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=timeout)
        finally:
            self.process = None
