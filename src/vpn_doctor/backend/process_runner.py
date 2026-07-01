"""Generic process runner used by VPN backends."""

from __future__ import annotations

import subprocess
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from vpn_doctor.backend.errors import BackendAlreadyRunningError, BackendProcessError

LineCallback = Callable[[str], None]


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
                args=(self.process.stdout, on_line),
                daemon=True,
            )
            self._reader_thread.start()

    def _read_output(self, stream, on_line: LineCallback) -> None:
        for line in stream:
            on_line(line.rstrip("\n"))

    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def terminate(self, timeout: float = 5.0) -> None:
        if self.process is None:
            return

        if not self.is_running:
            self.process = None
            return

        self.process.terminate()
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=timeout)
        finally:
            self.process = None
