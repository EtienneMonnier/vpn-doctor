# Internationalization Guide

VPN Doctor is English-first but must be translation-ready from the beginning.

## Rules

- All user-visible strings must be wrapped with gettext.
- Documentation starts in English.
- French is the first planned translation.

## Python usage

```python
from vpn_doctor.i18n import _

label = _("Connected")
```

## Planned structure

```text
po/
  vpn-doctor.pot
  fr.po
```
