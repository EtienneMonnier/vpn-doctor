# Plugin System

## Purpose

VPN Doctor should support multiple VPN engines without rewriting the application.

## Backend interface

Every backend should expose:

- `connect(profile)`
- `disconnect()`
- `status()`
- `diagnose(profile)`

Future additions:

- `supports(profile)`
- `import_profile(path)`
- `export_profile(profile)`
- `version()`

## Backend discovery

Early versions may register backends manually.

Later versions may use Python entry points:

```toml
[project.entry-points."vpn_doctor.backends"]
openfortivpn = "vpn_doctor.backend.openfortivpn:OpenFortiVPNBackend"
```

## Rule

A backend must not import GTK.
