# ADR-0013 - Approved Gateways

## Status

Accepted.

## Context

ADR-0012 allowed the helper with `auth_admin_keep`. The security review of
0.1.0 noted that, for a few minutes after a legitimate connection, another
process of the same user might start the helper without a prompt and connect
to a gateway of its own, with its own pinned certificate. openfortivpn then
applies that gateway's routes and DNS: a network man-in-the-middle position on
the whole computer. No root code execution, but a real risk.

Asking for the administrator password at every connection would close it, at
the cost of daily friction.

## Decision

Follow NetworkManager's model: an administrator approves a gateway once,
users connect to it freely.

- `/etc/vpn-doctor/gateways.json`, owned by root, mode 0644, lists approved
  gateways: host, port and pinned SHA-256 certificate fingerprint (or none
  for gateways trusted through the system CAs).
- The helper has three commands, each with its own polkit action selected
  by `org.freedesktop.policykit.exec.argv1`:

  | Command | Action | Active session |
  | --- | --- | --- |
  | `connect` | `io.github.vpndoctor.connect` | `yes` |
  | `approve` | `io.github.vpndoctor.approve` | `auth_admin` |
  | `revoke` | `io.github.vpndoctor.revoke` | `auth_admin` |

- `connect` refuses any gateway that is not approved, and any certificate
  other than the approved one. The helper reads the file with `O_NOFOLLOW`
  and refuses it unless it is owned by root and not writable by others.
- `approve` writes the file atomically (temporary file, `os.replace`).
- VPN Doctor reads the file without privileges to offer approval before the
  first connection, and lists approvals in Preferences with a Revoke button.

## Consequences

- One administrator password per gateway, then none: better for daily use and
  safer than `auth_admin_keep`.
- A process of the user can at most connect to a gateway already approved,
  with its approved certificate.
- When a gateway's certificate changes, the profile's `trusted_cert` and the
  approval must both be updated (the failure explains it).
- Inactive or remote sessions still need an administrator password.
