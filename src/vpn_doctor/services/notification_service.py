"""Desktop notification service."""

from __future__ import annotations

import logging
import shutil
import subprocess

LOGGER = logging.getLogger(__name__)


class NotificationService:
    """Send desktop notifications when supported."""

    def notify(self, title: str, message: str) -> None:
        if not shutil.which("notify-send"):
            LOGGER.debug("notify-send is not installed; notification skipped")
            return

        subprocess.run(
            ["notify-send", title, message],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
