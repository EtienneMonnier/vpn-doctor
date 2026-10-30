import gettext
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PO_DIR = Path(__file__).resolve().parents[1] / "po"
LANGUAGES = (PO_DIR / "LINGUAS").read_text(encoding="utf-8").split()
PLACEHOLDER = re.compile(r"\{[a-z_]*(?::[^}]*)?\}")

needs_gettext = pytest.mark.skipif(shutil.which("msgfmt") is None, reason="gettext is not installed")


@pytest.fixture(scope="module")
def localedir(tmp_path_factory):
    """Compile every translation with msgfmt --check (formats, headers, plurals)."""
    destination = tmp_path_factory.mktemp("locale")
    subprocess.run([str(PO_DIR / "compile.sh"), str(destination)], check=True)
    return destination


def catalog(localedir, language):
    path = localedir / language / "LC_MESSAGES" / "vpn-doctor.mo"
    with path.open("rb") as mo_file:
        return gettext.GNUTranslations(mo_file)._catalog


@needs_gettext
@pytest.mark.parametrize("language", LANGUAGES)
def test_translations_keep_every_placeholder(localedir, language):
    for key, translated in catalog(localedir, language).items():
        original = key[0] if isinstance(key, tuple) else key
        if not original:
            continue  # header
        assert sorted(PLACEHOLDER.findall(translated)) == sorted(PLACEHOLDER.findall(original)), (
            f"{language}: {original!r} -> {translated!r}"
        )


@needs_gettext
def test_vpn_doctor_speaks_french_with_compiled_translations(localedir):
    src = Path(__file__).resolve().parents[1] / "src"
    env = {
        **os.environ,
        "LANGUAGE": "fr",
        "VPN_DOCTOR_LOCALEDIR": str(localedir),
        "PYTHONPATH": str(src),
    }
    code = "from vpn_doctor.i18n import _; print(_('Connected'))"
    result = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True
    )

    assert result.stdout.strip() == "Connecté"


def test_rule_tables_are_translated_when_shown(monkeypatch):
    from vpn_doctor.diagnostics import log_rules

    monkeypatch.setattr(log_rules, "_", lambda text: f"<{text}>")
    rule = log_rules.LogRule(("marker",), "Name", "Message", None)

    item = rule.to_item()

    assert (item.name, item.message, item.suggestion) == ("<Name>", "<Message>", None)
