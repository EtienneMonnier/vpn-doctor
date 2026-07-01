# Profile Management

## Purpose

Profiles describe VPN configuration without secrets.

## Profile fields

- id;
- name;
- backend;
- host;
- port;
- username;
- realm;
- trusted certificate fingerprint;
- expected internal hosts;
- expected DNS servers;
- split tunnel preference.

## Storage

Early versions may use a JSON or TOML file.

Example future path:

```text
~/.config/vpn-doctor/profiles.toml
```

## Sanitized example

```toml
[[profiles]]
id = "demo-forti"
name = "Demo Fortinet"
backend = "openfortivpn"
host = "vpn.example.com"
port = 44443
username = "demo-user"
trusted_cert = "abcdef..."
```
