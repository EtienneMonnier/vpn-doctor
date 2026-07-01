"""Internationalization helpers."""

from __future__ import annotations

import gettext

APP_NAME = "vpn-doctor"

_translation = gettext.translation(APP_NAME, localedir="locale", fallback=True)
_ = _translation.gettext
