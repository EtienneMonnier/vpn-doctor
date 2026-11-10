# Sprint 8 Implementation Report: OpenVPN

## Summary

VPN Doctor now understands OpenVPN the way it understands openfortivpn:
it explains the usual OpenVPN failures from the NetworkManager plugin log,
and `vpn-doctor check-ovpn FILE` checks an `.ovpn` file before it is imported.

## Specification

- Diagnose before connecting: problems a file will cause are reported before
  `nmcli connection import`, not after a failed connection.
- Every rule is checked against the software users actually run: OpenVPN 2.7,
  OpenSSL 3 with Fedora's crypto policies, NetworkManager-openvpn 1.12.
- The file is only read. Private keys are never decoded; passwords found in
  the file are flagged, never shown.
- OpenVPN's own code (GPL-2.0) is not reused; only its log messages are
  matched.

## Implementation

### Failure explanations (`diagnostics/vpn_plugins.py`)

Seven rules, each placed before the generic rule it refines: weak
certificates (`ca md too weak`, `ee key too small`...), certificate dates,
legacy PKCS#12 files, TLS version, `tls-auth` / `tls-crypt` key mismatch, data
cipher negotiation, compression pushed by the server. Markers were taken from
the strings of the installed `openvpn` binary and `libcrypto`.

### `check-ovpn` (`diagnostics/ovpn_check.py`)

What NetworkManager does with each option was measured, not guessed: every
option was imported into a temporary connection (`nmcli connection import
--temporary`, deleted right after) and the result compared with a file
without it. Findings:

- dropped silently although they matter: `redirect-gateway`, `route-nopull`,
  `pull-filter`, `dhcp-option`, `remote-cert-eku`, `ncp-ciphers` (old name of
  `data-ciphers`), `route-ipv6`;
- imported although OpenVPN 2.7 refuses it: `tls-remote`;
- a file that does not exist is imported as a dangling path;
- inline blocks are copied to
  `~/.local/share/networkmanagement/certificates/nm-openvpn/`.

Checks: structure (no `remote`, static key, damaged file), removed and
deprecated options, missing files (with the exact fix when the file sits next
to the configuration), ciphers (BF-CBC and other 64-bit ciphers are not
available at all with OpenSSL 3; 3DES is deprecated), weak packet
authentication, compression, missing server verification, `tls-auth` without
key direction, `tls-version-max` 1.0/1.1, dropped options, passwords in the
file, and certificates through the `openssl` command (expired, not yet valid,
expiring within 30 days, RSA/DSA under 2048 bits, MD5/SHA-1 signatures except
on self-signed roots).

Exit code 1 only for errors: warnings describe a connection that will work,
differently or less safely.

## Validation on real files

The checker ran on one file of each of the 52 providers of
[haugene/vpn-configs-contrib](https://github.com/haugene/vpn-configs-contrib),
a public collection of OpenVPN files (kept outside the repository, GPL-3.0).

- It found two false positives, fixed before release: CA bundles keeping an
  old expired CA next to its replacement are fine (OpenVPN uses the valid
  one), so an expired or weak CA is an error only when no valid CA comes with
  it.
- It found real problems in that collection: committed merge conflict
  markers, a misspelled option (`data-ciphers-fallbacks`, refused by OpenVPN),
  CA certificates expired since 2020-2023, 1024-bit CA keys, compression and
  absolute paths that only exist inside their Docker image.

## Tests

`tests/test_vpn_plugins.py` (log rules) and `tests/test_ovpn_check.py`
(parser, every check, CA bundles, damaged files, inline passwords never
echoed, a real certificate read with `openssl`, CLI text, JSON and exit
codes).

## Review notes

- The option lists are tied to NetworkManager-openvpn 1.12; a later version
  may import more options. The measuring method is described above so the
  lists can be refreshed.
- Not covered yet: PKCS#12 files (their encryption can only be read with the
  password), `connection` blocks, and the GUI (an "Import an OpenVPN file…"
  entry that runs the check first would be the natural next step).
