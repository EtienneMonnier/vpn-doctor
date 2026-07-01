# Diagnostics Guide

## Purpose

Diagnostics are the main differentiator of VPN Doctor.

VPN Doctor should explain problems that normal VPN clients hide.

## Diagnostic result model

Each result should include:

- check id
- title
- status
- severity
- explanation
- technical details
- suggested fix
- whether the fix is automatic
- whether the fix is safe

## Severity

Suggested severities:

- `ok`
- `info`
- `warning`
- `error`
- `critical`

## Pre-connection checks

- Backend installed
- Gateway format valid
- Gateway reachable
- Port reachable
- Certificate readable
- Certificate fingerprint known
- Profile has required fields

## Connection checks

- Process started
- Gateway connected
- Authentication accepted
- MFA/SAML detected
- VPN address allocated
- Interface created
- Tunnel up

## Post-connection checks

- VPN interface present
- IP address assigned
- Routes installed
- DNS servers installed
- Internal host reachable
- Internet reachable
- Split/full tunnel detected
- Existing default route preserved if requested

## Example diagnosis

```text
Problem:
Tunnel is up, but internal server is unreachable.

Evidence:
ICMP requests leave ppp0, but no replies return.

Possible cause:
Backend-specific tunnel issue or remote firewall/policy issue.

Suggested fix:
Try the OpenFortiVPN backend instead of NetworkManager FortiSSLVPN.
```

## Report export

VPN Doctor should eventually export diagnostic reports in:

- Markdown
- HTML
- JSON

Reports must redact secrets.
