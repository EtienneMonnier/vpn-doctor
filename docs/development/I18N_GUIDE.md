# Internationalization Guide

VPN Doctor is written in English and translated with GNU gettext. Languages:
see `po/LINGUAS` (French, German, Spanish, Italian, Dutch, Portuguese,
Polish).

## Rules

- Every user-visible string goes through gettext: GUI, CLI messages and help,
  diagnostic names, messages and suggestions.
- Log messages for developers (`LOGGER.*`) stay in English.
- The privileged helper stays in English: it runs as root with the standard
  library only (ADR-0012).
- Profile names, connection names and skin metadata are data: never
  translated.
- Program names, commands, options and menu paths of other applications
  (Remmina, GNOME Settings) stay in English inside translations.

## Python usage

```python
from vpn_doctor.i18n import N_, _, ngettext

label = _("Connected")

# Variables: named placeholders with str.format, never f-strings or
# concatenation, so translators can move them.
message = _("{target} is not reachable ({error}).").format(target=target, error=error)

# Plurals: ngettext, even when English uses the same form.
title = ngettext(
    "⚠ {count} network conflict: {first}",
    "⚠ {count} network conflicts: {first}",
    count,
).format(count=count, first=first)

# Strings defined at import time (rule tables, dicts): N_() marks them,
# _() translates them where they are shown.
REASONS = {1: N_("the server requires TLS")}
reason = _(REASONS[code])
```

Diagnostic rule tables (`LogRule`) use `N_()`; `LogRule.to_item()` translates
them. Add a `# TRANSLATORS:` comment above a string whose context is not
obvious.

Never name a local variable `_` (for example `host, _, port = ...`): it hides
the translation function in the whole function.

## Workflow

```bash
po/update.sh                  # extract po/vpn-doctor.pot, merge into po/*.po
# translate the new or fuzzy entries of po/<lang>.po
po/compile.sh build/locale    # msgfmt --check every language
pytest tests/test_translations.py
```

Run `po/update.sh` after changing user-visible text and commit the updated
`.pot` and `.po` files with the change. `tests/test_translations.py` compiles
every language and checks that translations keep every `{placeholder}`.

To add a language, add its code to `po/LINGUAS` and run `po/update.sh`.

## Where translations are read

`vpn_doctor.i18n` reads `$VPN_DOCTOR_LOCALEDIR` when set, otherwise the
system directory (`/usr/share/locale`).

- `launch.sh` compiles `po/` into `build/locale` and sets the variable.
- The RPM compiles `po/` into `/usr/share/locale` (`%find_lang`).
- Tests force English (`LANGUAGE=C` in `tests/conftest.py`).

The language follows the usual variables: `LANGUAGE`, `LC_ALL`,
`LC_MESSAGES`, `LANG`. Scripts and agents that need English output run
`LANGUAGE=en vpn-doctor ...`.

## Quality

The first translations were produced with AI assistance and reviewed for
consistency (placeholders, product names, GNOME terminology). Native speakers
are welcome to improve them: edit `po/<lang>.po`, set `Last-Translator`, and
run the workflow above.
