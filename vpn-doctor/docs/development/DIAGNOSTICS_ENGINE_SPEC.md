# Diagnostics Engine Specification

## Purpose

The diagnostics engine turns low-level checks into human-readable explanations.

VPN Doctor should explain:

- what was tested;
- what passed;
- what failed;
- what the failure probably means;
- what the user can try next.

## Diagnostic model

A diagnostic report contains multiple diagnostic items.

Each item has:

- name;
- success flag;
- severity;
- message;
- suggestion.

## Severity levels

| Severity | Meaning |
| --- | --- |
| info | useful state |
| warning | potential issue |
| error | blocking issue |

## Diagnostic categories

### Pre-connection

- binary installed;
- gateway DNS resolution;
- gateway TCP reachability;
- certificate trust;
- local network available.

### During connection

- gateway connected;
- authentication started;
- authentication succeeded;
- VPN configuration received;
- tunnel interface created.

### Post-connection

- PPP interface exists;
- VPN IP assigned;
- routes installed;
- DNS installed;
- corporate host reachable;
- internet still reachable when split tunnel is expected.

## Explainability rule

Every failed diagnostic should include a concrete suggestion.

Example:

```text
Gateway certificate validation failed.
Suggestion: verify the fingerprint with your administrator and add it as trusted-cert.
```

## Future report formats

- terminal output;
- GTK report view;
- Markdown export;
- JSON export;
- support bundle with sanitized logs.
