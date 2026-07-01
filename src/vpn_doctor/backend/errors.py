"""Backend exceptions."""

from __future__ import annotations


class BackendError(Exception):
    """Base backend error."""


class BackendNotFoundError(BackendError):
    """Raised when a requested backend is not registered."""


class BackendAlreadyRunningError(BackendError):
    """Raised when a backend process is already running."""


class BackendProcessError(BackendError):
    """Raised when a process cannot be started or stopped safely."""
