# Secret Management

## Goal

Use the Linux Secret Service API for passwords and tokens.

GNOME Keyring is the reference implementation.

## Design

`VPNProfile` must not store passwords; profile files containing `password`,
`secret` or `token` keys are rejected.

Flow for direct backends (openfortivpn):

1. User selects a profile.
2. Controller asks `KeyringSecretStore` (libsecret) for the password.
3. If none is remembered, the UI asks for it and offers "Remember in the
   keyring".
4. Backend receives the password only at runtime, through stdin.
5. When openfortivpn asks another question (PEM pass phrase), the backend
   calls a `prompt_handler`; the controller answers from the keyring or
   leaves the prompt to the UI.
6. Secrets are never logged; the log shows "(answered from the keyring)".

NetworkManager connections do not use this flow: NetworkManager asks the
GNOME secret agent itself.

## Keyring entries

| Attribute | Value |
| --- | --- |
| schema | `io.github.vpndoctor.Secret` |
| `profile` | profile name |
| `kind` | `password` or `pem-passphrase` |

One-time codes (OTP, two-factor tokens) are never stored.

Remove the entries of a profile with:

```bash
vpn-doctor forget-secrets --profile "Office"
```

## Using KeePassXC

The code talks to the Secret Service API, not to GNOME Keyring directly.
To keep these secrets in KeePassXC, enable *Settings > Secret Service
Integration* in KeePassXC and disable the secrets component of GNOME Keyring.
NetworkManager passwords then move to KeePassXC too.
