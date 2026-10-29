# ADR-0012 - Dedicated Privileged Helper

## Status

Accepted. Supersedes the `pkexec openfortivpn` approach of ADR-0010 when VPN
Doctor is installed from a package.

## Context

ADR-0010 started `openfortivpn` through `pkexec`. Two problems remained:

- the polkit rule was the generic `org.freedesktop.policykit.exec`: any
  argument could be passed to a root `openfortivpn`;
- `pkexec` replaces itself with `openfortivpn`, so the user could not signal
  it and disconnecting needed a second authentication (`pkexec kill`).

## Decision

- A small helper, `/usr/libexec/vpn-doctor/vpn-doctor-helper`
  (`src/vpn_doctor/privileged_helper.py`), is the only code running as root.
- A dedicated polkit action, `io.github.vpndoctor.helper`, allows only that
  program, with `auth_admin_keep` for active local sessions.
- VPN Doctor sends the profile as one JSON line on stdin. The helper accepts
  a fixed list of fields, validates each one and builds the `openfortivpn`
  command itself, always with `-c /dev/null`. It never runs a command line
  received from the user.
- Certificate and key files must be regular PEM files owned by the caller
  (`PKEXEC_UID`), or owned by root under `/etc/openfortivpn/`. The helper
  opens them itself and hands the open descriptor (`/dev/fd/N`) to
  openfortivpn, so a path swapped after the check has no effect.
- The helper stays the parent of `openfortivpn` and stops it when its stdin
  closes. VPN Doctor disconnects by closing the pipe: one authentication per
  connection, and a crashed VPN Doctor never leaves a tunnel behind.
- The helper is written in Python with the standard library only, run with
  `python3 -I` from a root-owned location. Python is memory-safe like Rust
  for this purpose, and keeps the package `noarch` without a new toolchain.
  The security comes from the narrow interface, not from the language.

## Consequences

- Without the installed helper (development checkout), VPN Doctor falls back
  to ADR-0010.
- Options outside the accepted fields (pppd plugins, routes, DNS options)
  cannot be passed to openfortivpn from VPN Doctor. They can be added to the
  helper one by one, with validation and tests.
