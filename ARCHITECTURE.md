# Architecture

VPN Doctor should be structured around diagnostics, not around direct VPN ownership.

## High-level components

```text
GUI / CLI
   |
Diagnostic Engine
   |
   +-- NetworkManager Inspector
   +-- Backend Test Runner
   +-- Route Analyzer
   +-- DNS Analyzer
   +-- Certificate Analyzer
   +-- Traffic Analyzer
   +-- Report Generator
```

## Backend philosophy

VPN Doctor should not reimplement VPN protocols.

It should use existing tools:

- NetworkManager
- openfortivpn
- openconnect
- openvpn
- wg / wg-quick
- strongSwan / nm-strongswan

## Diagnostic flow

1. Read VPN profile.
2. Identify backend type.
3. Check gateway reachability.
4. Check certificate and trust status.
5. Start or inspect tunnel.
6. Inspect interface.
7. Inspect routes.
8. Inspect DNS.
9. Run connectivity tests.
10. Compare with direct backend if available.
11. Produce diagnosis.
12. Suggest fixes.

## Repair model

Repairs must be explicit and reversible.

The application should show:

- what will be changed;
- why it will be changed;
- the exact command or file modification;
- how to undo it.

## Privileges

Most checks can run as user.

Privileged operations should be isolated:

- route changes;
- NetworkManager profile modifications;
- packet captures;
- starting some VPN clients;
- writing system configuration.

Potential approach:

- use `pkexec` for specific actions;
- avoid running the whole GUI as root;
- never store passwords in plain text.
