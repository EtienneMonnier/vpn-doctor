# Sprint 5.1 Implementation Report

## Summary

Visual identity and preferences.

## Added

- Logo: a shield (protect), a cross (diagnose) and a pulse (the health of the
  connection). Two variants drawn with VectorCraft from
  `assets/logo/generate_logo.py`; copies ship in `src/vpn_doctor/ui/assets/`,
  including a hicolor app icon.
- Startup animation: the skin's logo and boot lines that report real checks
  (NetworkManager, keyring, number of connections). A click or a key skips it;
  Preferences turns it off. Not a separate splash window, per GNOME HIG.
- Preferences (`Adw.PreferencesDialog`): skin, custom skins folder and reload,
  startup animation, forget secrets of each openfortivpn profile.
- About dialog (`Adw.AboutDialog`).
- `@logo` skin metadata, restricted to the skin's folder or built-in assets.

## Fixed

- Conflict checks: nmcli reports the Wi-Fi device as the IP interface of
  OpenVPN connections; the tunnel is now found by its address.

## Validation

```bash
ruff check src tests
pytest            # 113 passed
```

Rendered with both skins: startup animation, main window, preferences.
Three VPNs (WireGuard, OpenVPN, openfortivpn) were connected at once on the
developer's machine; `vpn-doctor conflicts` found none after the fix.

## Review notes

- The app icon is only registered for the running process (icon search
  path); installing it system-wide belongs to packaging (Sprint 6).
- Requires libadwaita >= 1.5 (AlertDialog, PreferencesDialog, AboutDialog).
