"""Privilege escalation policy for VPN backends.

openfortivpn must run as root to create the PPP interface and routes. VPN
Doctor itself stays unprivileged and asks polkit, through pkexec, only for the
backend process. See docs/adr/0010-pkexec-privilege-escalation.md.
"""

from __future__ import annotations

import os
import shutil


def default_privilege_command() -> tuple[str, ...]:
    """Return the command prefix used to start privileged backend processes."""
    if os.geteuid() == 0:
        return ()

    if shutil.which("pkexec"):
        return ("pkexec",)

    return ()
