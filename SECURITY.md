# Security Policy

## Reporting a vulnerability

Please do not open a public issue for a security problem.

Report it privately through GitHub: **Security → Report a vulnerability** on
this repository (private vulnerability reporting). Describe the problem, the
affected version and how to reproduce it. You should get an answer within a
week.

Never include real passwords, private keys, VPN gateway addresses or
unredacted logs in a report; use placeholders such as `vpn.example.com`,
`demo-user` and `192.0.2.0/24`.

## Scope

The most sensitive part of VPN Doctor is the privileged helper
(`/usr/libexec/vpn-doctor/vpn-doctor-helper`) and its polkit policy: it is the
only code running as root. See `docs/adr/0012-privileged-helper.md` and
`docs/adr/0013-approved-gateways.md`.

## Supported versions

Only the latest release receives security fixes.
