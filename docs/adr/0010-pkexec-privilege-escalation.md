# ADR-0010 - Privilege Escalation Through pkexec

## Status

Accepted. Superseded by ADR-0012 when the helper is installed.

## Context

`openfortivpn` must run as root to create the PPP interface, routes and DNS
configuration. Running it as a normal user fails with:

```text
ERROR:  This process was not spawned with root privileges, which are required.
```

VPN Doctor itself, and especially the GTK UI, must not run as root.

When `openfortivpn` runs as root it also reads `/etc/openfortivpn/config`. On a
real workstation that file may belong to another gateway and contain a
username, a password or client certificates, which would be silently merged
into the VPN Doctor profile.

## Decision

- VPN Doctor stays unprivileged. Only the backend process is elevated.
- When VPN Doctor is not root, the backend command is prefixed with `pkexec`
  (`services/privilege_service.py`). On a desktop session, polkit shows the
  standard administrator authentication dialog.
- `pkexec` replaces itself with `openfortivpn`, so the user can no longer signal
  the process. Disconnection falls back to `pkexec kill -TERM <pid>`.
- The command always contains `-c /dev/null`: the VPN Doctor profile is the
  only source of options.
- The VPN password still travels through stdin only, never through argv.

## Consequences

- Connecting and disconnecting each trigger one polkit prompt with the default
  `auth_admin` policy.
- A cancelled polkit prompt is reported as a privilege error with a readable
  suggestion.
- Options from `/etc/openfortivpn/config` are ignored on purpose. Users must
  move them into a VPN Doctor profile.

## Future work

Ship a dedicated polkit action and a minimal privileged helper, so a single
authorization covers connect and disconnect and only the `openfortivpn`
binary can be started. This is required before packaging (Sprint 6).
