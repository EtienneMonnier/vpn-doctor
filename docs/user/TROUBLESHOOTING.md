# Troubleshooting

This page will collect common VPN issues and explanations.

## Certificate not trusted

Meaning:

The VPN gateway uses a certificate that your system does not trust.

Safe fix:

Only trust the fingerprint if your IT administrator confirms it.

## Connected but no Internet

Possible cause:

The VPN pushed a full-tunnel default route.

## Connected but internal servers unreachable

Possible causes:

- Missing route.
- DNS issue.
- Remote firewall.
- Backend-specific tunnel problem.
