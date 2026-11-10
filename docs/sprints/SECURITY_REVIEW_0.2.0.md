# Security review before going public (0.2.0)

Date: 2026-11-10. Scope: the whole repository and its history, before making
the GitHub repository public again.

## Incident that started it

The repository had been public since its creation, and its first commits
(Sprint 0 to 2) held the real details of a customer FortiGate gateway used to
validate VPN Doctor: address and port, VPN user name, authentication realm and
certificate fingerprint. No password, private key or certificate was ever
committed. The details had been removed from the files later, but stayed in the
history.

Actions taken:

- repository made private;
- history rewritten with `git filter-repo`, every value replaced by the
  documentation placeholders (`192.0.2.10`, `demo-user`, `abcdef...`);
- old repository deleted (its pull request refs still pointed at the old
  commits) and a new private one created from the rewritten history;
- the customer's IT was to be told what was exposed and for how long.

Lesson: real endpoints must never reach a commit, even in a first draft.
`AGENTS.md` already said so; the scan below is now part of the release
checklist.

## 1. Secrets and identifying details

- `gitleaks git` over all 46 commits: no leak found.
- Manual search of the history (`git log --all -p`) for the names of real
  customers and connections, public IP addresses outside the documentation
  ranges, 64-hex fingerprints, PEM blocks, passwords, home paths and domain
  names: nothing left except test placeholders and fake keys in tests.
- Case studies in `docs/case-studies/` are sanitized.
- The author's work e-mail was replaced by the GitHub noreply address in
  every commit and in the RPM changelog (second history rewrite); the
  repository's `user.email` now uses the noreply address.
- The terminal artwork used by the Wasteland build stays out of the
  repository (`.gitignore`): it resembles a game's trade dress.

## 2. Privileged helper and polkit policy

`src/vpn_doctor/privileged_helper.py` re-read in full after the changes of
ADR-0013. No vulnerability found:

- strict field list, values validated by regular expressions; user name and
  realm cannot start with `-`, so no option injection; host and port are
  validated and the command is built by the helper, never by the caller;
- only `/usr/bin/openfortivpn` with `-c /dev/null` (no system config file),
  through `/usr/bin/stdbuf`, with a fixed environment;
- PEM files: resolved, opened with `O_NOFOLLOW | O_NONBLOCK`, checked with
  `fstat` on the open descriptor (regular file, owner, PEM header) and handed
  over as `/dev/fd/N`, so swapping the path after the check has no effect;
- approved gateways: file must be root-owned and not writable by group or
  others, written atomically in a root-owned directory;
- `PKEXEC_UID` required; the installed helper keeps `#!/usr/bin/python3 -I`
  (checked on the 0.2.0 RPM, the open point of the Sprint 6 review);
- policy: `connect` without password for an active local session (only to
  approved gateways), `approve` and `revoke` need an administrator.

Design observation, accepted: root-owned certificate and key files under
`/etc/openfortivpn/` can be used by any user with an active session on the
computer, towards an approved gateway. They still need that VPN account's
password, and the tunnel only reaches gateways an administrator approved. On a
shared computer, keep client certificates in the user's own home instead.

## 3. Secrets at run time

- No password, answer or pass phrase is logged: answers go to openfortivpn's
  stdin only; the GUI log says "(answered from the keyring)".
- Profiles refuse `password`, `passwd`, `secret` and `token` keys; secrets
  live in the desktop keyring (libsecret).
- GUI password input uses `Gtk.PasswordEntry`; the CLI uses `getpass`.
- No `shell=True` anywhere; every subprocess gets an argument list.

## 4. Public project hygiene

- `SECURITY.md`: private vulnerability reporting.
- Bug report template warns that issues are public and asks for redacted
  logs.
- CI workflow runs with `permissions: contents: read`.
- To do when the repository becomes public: enable private vulnerability
  reporting and protect `main` (not available for private repositories on
  the free plan).
