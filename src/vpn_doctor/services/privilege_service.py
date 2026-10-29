"""Privilege escalation policy for VPN backends.

openfortivpn must run as root to create the PPP interface and routes. VPN
Doctor itself stays unprivileged and asks polkit, through pkexec, only for the
backend process. See docs/adr/0010-pkexec-privilege-escalation.md and
docs/adr/0012-privileged-helper.md.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

HELPER_PATH = Path("/usr/libexec/vpn-doctor/vpn-doctor-helper")


def default_privilege_command() -> tuple[str, ...]:
    """Return the command prefix used to start privileged backend processes."""
    if os.geteuid() == 0:
        return ()

    if shutil.which("pkexec"):
        return ("pkexec",)

    return ()


def helper_command(helper: Path = HELPER_PATH) -> tuple[str, ...]:
    """Return the command starting the installed privileged helper, if any.

    Packages install the helper and its polkit policy. Without them (e.g. a
    development checkout), VPN Doctor falls back to `pkexec openfortivpn`.
    """
    if not os.access(helper, os.X_OK):
        return ()
    if os.geteuid() == 0:
        return (str(helper), "connect")
    if shutil.which("pkexec"):
        return ("pkexec", str(helper), "connect")
    return ()
