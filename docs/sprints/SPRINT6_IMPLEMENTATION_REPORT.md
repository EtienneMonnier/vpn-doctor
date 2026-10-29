# Sprint 6 Implementation Report (0.1.0)

## Summary

A dedicated privileged helper replaces `pkexec openfortivpn`, and VPN Doctor
ships as an RPM.

## Added

- `vpn-doctor-helper` (ADR-0012) and the `io.github.vpndoctor.helper`
  polkit action.
- RPM spec, build script, desktop launcher, AppStream metainfo, icon.
- "New VPN connection…" (+ menu) and "Settings…" (NetworkManager tabs).
- Preferences: default connection, auto-connect at startup.

## Validation

```bash
ruff check src tests
pytest            # 137 passed
desktop-file-validate data/io.github.vpndoctor.VPNDoctor.desktop
appstreamcli validate --no-net data/io.github.vpndoctor.VPNDoctor.metainfo.xml
xmllint --dtdvalid /usr/share/polkit-1/policyconfig-1.dtd data/io.github.vpndoctor.helper.policy
```

The helper's abuse cases are tested (option injection, unknown fields,
non-PEM files, files of other users, running outside pkexec, stop on stdin
close). The installed RPM still has to be validated by hand.

## Review notes

- The helper is Python (standard library, `python3 -I`); Rust was considered,
  see ADR-0012.
- DEB packaging and a NetworkManager-only Flatpak remain to do.
