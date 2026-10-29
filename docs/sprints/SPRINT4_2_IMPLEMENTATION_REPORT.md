# Sprint 4.2 Implementation Report

## Summary

Secrets of direct openfortivpn profiles go to the desktop keyring, so a
gateway with a client certificate no longer asks for the PEM pass phrase at
every connection.

## Added

- `KeyringSecretStore` (libsecret) and `classify_prompt`.
- Prompt handler hook in the openfortivpn backend; the controller answers
  from the keyring.
- "Remember in the keyring" in the UI dialogs.
- `vpn-doctor forget-secrets`.
- `PRIVATE_KEY_ERROR` log kind with a suggestion.

## Validation

```bash
ruff check src tests
pytest            # 98 passed
```

libsecret store, lookup and clear were checked against the real GNOME Keyring
with a throwaway entry, removed afterwards.

## Review notes

- Secret Service on the test machine is GNOME Keyring; KeePassXC requires
  enabling its Secret Service integration (documented).
- A remembered wrong password is not cleared automatically; the failure
  suggestion points to `forget-secrets`. A UI action comes with the
  Preferences menu.
