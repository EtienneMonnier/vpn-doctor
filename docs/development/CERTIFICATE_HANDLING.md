# Certificate Handling

## Problem

FortiGate SSL VPN deployments often use a certificate that Linux clients do not trust
automatically. `openfortivpn` then reports:

```text
Gateway certificate validation failed.
```

## Safe workflow

1. Display the certificate fingerprint.
2. Tell the user to verify it with the administrator.
3. Store only the trusted fingerprint in the profile.
4. Never silently trust a certificate.

## Future diagnostic

VPN Doctor should detect this error and explain:

- what a certificate fingerprint is;
- why validation failed;
- how to verify it safely;
- how to update the profile.
