# Sprint 7.2 Implementation Report

## Summary

VPN Doctor is translated into French, German, Spanish, Italian, Dutch,
Portuguese and Polish: GUI, CLI messages and help, and every diagnostic
explanation.

## Specification

- Every user-visible string goes through gettext; developer logs and the
  privileged helper stay in English.
- Translations are found once installed (`/usr/share/locale`) and from the
  source tree (`launch.sh`).
- Placeholders are named (`{name}`) so translators can move them; plurals use
  `ngettext`.
- Tests stay in English whatever the developer's language.

## Implementation

- `i18n.py`: `$VPN_DOCTOR_LOCALEDIR`, else the system locale directory (the
  old relative `locale` folder never worked once installed); `N_()` and
  `ngettext`.
- About 170 strings marked in the CLI, the backends, the services and the
  diagnostics. Rule tables (`LogRule`, RDP negotiation codes, openfortivpn
  failure suggestions) are marked with `N_()` and translated when shown.
- f-strings in messages replaced by `_("…{name}…").format(...)`.
- Two `host, _, port = ...` unpackings renamed: they hid `_`.
- `po/update.sh`, `po/compile.sh`, `po/LINGUAS`; 285 messages.
- `launch.sh` compiles into `build/locale`; the RPM compiles into
  `%{_datadir}/locale` with `%find_lang` (`BuildRequires: gettext`).
- `tests/conftest.py` sets `LANGUAGE=C`; `tests/test_translations.py`
  compiles every language with `msgfmt --check`, checks placeholders, and
  runs VPN Doctor in French.

## Validation

```bash
ruff check src tests
pytest                       # 176 passed
po/compile.sh build/locale   # 7 x 285 translated messages, msgfmt --check
LANGUAGE=fr ./launch.sh --help
LANGUAGE=fr ./launch.sh rdp 127.0.0.1 --port 1
LANGUAGE=pl ./launch.sh rdp 127.0.0.1 --port 1 --json
packaging/rpm/build.sh       # the RPM ships the 7 .mo files
```

The GUI module and the startup animation lines were loaded in French and
Polish (plural forms checked). The GUI window itself was not opened.

## Review notes

- Translations were produced with AI assistance, one language at a time,
  with placeholder checks; the French one was reviewed by hand. Native
  speakers should review the others.
- Terminology choices: "Skin" is "Thème"/"Tema"/"Thema" in most languages
  (kept "Skin" in German); FortiGate's "realm" stays in English; menu paths
  of Remmina and Windows group names stay in English because they identify
  exact labels.
- argparse's own words ("usage:", "positional arguments") and OS error
  messages (`Connection refused`) stay in English: Python ships no
  translations for them.
- Not translated yet: the desktop file and the AppStream metainfo.
