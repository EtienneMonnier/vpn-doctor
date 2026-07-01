# Security Guide

## Core rule

VPN Doctor handles sensitive infrastructure data.

Security must be part of the design from day one.

## Never store in files

- VPN passwords
- MFA tokens
- private keys
- private certificates
- customer-specific secrets

## Secrets storage

Use Secret Service / GNOME Keyring.

Password lookup keys should include:

- application name
- profile id
- backend type

## Logging rules

Never log:

- passwords
- tokens
- full private certificates
- session cookies

Mask values:

```text
password=<redacted>
token=<redacted>
```

## Profiles

Profiles may store:

- display name
- backend type
- gateway
- port
- username
- realm
- trusted certificate fingerprint
- expected DNS
- expected routes

Profiles must not store:

- password
- private key content
- MFA seed

## Case studies

Public case studies must be sanitized.

Use:

```text
vpn.example.com
203.0.113.10
192.0.2.0/24
```

instead of real production data.

## Certificate handling

When certificate fingerprint changes:

- show old fingerprint
- show new fingerprint
- explain risk
- require explicit user confirmation
- never silently trust a new certificate
