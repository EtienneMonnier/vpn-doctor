# Security Guide

## Core rule

VPN Doctor must never leak secrets.

## Forbidden in repository

- passwords;
- tokens;
- private keys;
- real customer VPN endpoints;
- unredacted logs;
- sensitive certificate material.

## Profile safety

Profiles may contain configuration but not passwords.

Allowed:

- backend;
- host;
- port;
- username if user agrees;
- realm;
- trusted certificate fingerprint.

Forbidden:

- password;
- MFA token;
- private key passphrase.

## Logging

Logs must redact:

- passwords;
- tokens;
- command stdin;
- private key material.

## Subprocess safety

Avoid shell execution.

Use:

```python
subprocess.Popen(["openfortivpn", "vpn.example.com:443"])
```

Avoid:

```python
subprocess.Popen("openfortivpn vpn.example.com:443", shell=True)
```
