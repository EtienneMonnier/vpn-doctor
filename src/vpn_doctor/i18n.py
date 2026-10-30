"""Internationalization helpers.

Translations are looked up in `$VPN_DOCTOR_LOCALEDIR` when it is set (source
tree, see launch.sh), otherwise in the system locale directory
(/usr/share/locale), where packages install them.

Strings defined at import time, such as diagnostic rule tables, are marked
with N_() and translated with _() when they are shown.
"""

from __future__ import annotations

import gettext
import os

APP_NAME = "vpn-doctor"
LOCALEDIR_VARIABLE = "VPN_DOCTOR_LOCALEDIR"


def localedir() -> str | None:
    """None means Python's default, <prefix>/share/locale."""
    return os.environ.get(LOCALEDIR_VARIABLE) or None


_translation = gettext.translation(APP_NAME, localedir=localedir(), fallback=True)
_ = _translation.gettext
ngettext = _translation.ngettext


def N_(message: str) -> str:
    """Mark a string for extraction without translating it yet."""
    return message
