"""Skins for the GTK UI.

A skin is a plain GTK CSS file. Optional metadata lives in its first comment:

    /*
     * @name: Wasteland Terminal
     * @color-scheme: dark
     * @title: VPN-DOCTOR 3000
     * @tagline: Wasteland network diagnostics
     */

Built-in skins ship in vpn_doctor/ui/themes/. Users add their own by dropping a
.css file in ~/.config/vpn-doctor/themes/; a user skin with the same file name
overrides a built-in one. The UI documents the CSS classes it exposes in
docs/development/THEMES.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

BUILTIN_THEME_DIR = Path(__file__).resolve().parent.parent / "ui" / "themes"
DEFAULT_THEME = "default"

_METADATA = re.compile(r"@([a-z-]+)\s*:\s*(.+?)\s*(?:\*/)?\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Theme:
    """A skin and its metadata."""

    id: str
    name: str
    path: Path
    color_scheme: str = "default"  # default, light or dark
    title: str | None = None
    tagline: str | None = None
    builtin: bool = True

    def css(self) -> str:
        return self.path.read_text(encoding="utf-8")


def parse_theme(path: Path, builtin: bool) -> Theme:
    """Read the metadata of a skin file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    header = text[: text.find("*/") + 2] if text.lstrip().startswith("/*") else ""
    meta = dict(_METADATA.findall(header))
    color_scheme = meta.get("color-scheme", "default")
    if color_scheme not in {"default", "light", "dark"}:
        color_scheme = "default"
    return Theme(
        id=path.stem,
        name=meta.get("name", path.stem.replace("-", " ").title()),
        path=path,
        color_scheme=color_scheme,
        title=meta.get("title"),
        tagline=meta.get("tagline"),
        builtin=builtin,
    )


class ThemeService:
    """List and resolve skins."""

    def __init__(self, user_dir: Path | None = None, builtin_dir: Path = BUILTIN_THEME_DIR) -> None:
        self.user_dir = user_dir or Path.home() / ".config" / "vpn-doctor" / "themes"
        self.builtin_dir = builtin_dir

    def themes(self) -> list[Theme]:
        found: dict[str, Theme] = {}
        for directory, builtin in ((self.builtin_dir, True), (self.user_dir, False)):
            if directory.is_dir():
                for path in sorted(directory.glob("*.css")):
                    found[path.stem] = parse_theme(path, builtin)
        default = found.pop(DEFAULT_THEME, None)
        ordered = sorted(found.values(), key=lambda theme: theme.name.lower())
        return [default, *ordered] if default else ordered

    def get(self, theme_id: str | None) -> Theme:
        """Return the requested skin, falling back to the default one."""
        themes = {theme.id: theme for theme in self.themes()}
        return themes.get(theme_id or DEFAULT_THEME) or themes[DEFAULT_THEME]
