# Internationalization Guide

## Default language

English is the source language.

French is the first planned translation.

## Rule

Every user-visible string must use gettext.

```python
from vpn_doctor.i18n import _

label = _("Connected")
```

## Avoid string concatenation

Bad:

```python
_("Connected to ") + gateway
```

Better:

```python
_("Connected to {gateway}").format(gateway=gateway)
```

## Files

Suggested structure:

```text
po/
  vpn-doctor.pot
  fr.po

locale/
  fr/LC_MESSAGES/vpn-doctor.mo
```

## Developer notes

- Do not translate log codes.
- Translate UI labels.
- Translate user-facing explanations.
- Keep technical commands unchanged.
