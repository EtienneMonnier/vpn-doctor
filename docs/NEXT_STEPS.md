# Next Steps

## 1. Create the Git repository

Suggested name:

```text
vpn-doctor
```

Initial structure:

```text
vpn-doctor/
  README.md
  ROADMAP.md
  ARCHITECTURE.md
  docs/
  src/
  tests/
  assets/
```

## 2. Build the first prototype

Start with a CLI prototype before building the GUI.

Command idea:

```bash
vpn-doctor diagnose --type fortinet --gateway 195.135.0.91 --port 44443 --user rentplus
```

The CLI should run:

- TCP port check;
- certificate fingerprint check;
- NetworkManager profile inspection;
- route inspection;
- DNS inspection;
- optional `openfortivpn` comparison.

## 3. Generate a diagnostic report

Output should be both human-readable and machine-readable.

Example:

```text
[OK] Gateway reachable on 195.135.0.91:44443
[WARN] Certificate is self-signed
[OK] trusted-cert configured
[WARN] NetworkManager plugin connected but no traffic returned
[OK] openfortivpn backend works
[RECOMMENDATION] Use openfortivpn backend for this profile
```

## 4. Add GTK/libadwaita GUI

Only after the diagnostic engine is useful.

The GUI should display:

- profile;
- status;
- diagnostic progress;
- logs;
- recommended fixes;
- export button.

## 5. Add secure secret storage

Use Secret Service / GNOME Keyring.

Do not store VPN passwords in plain text.

## 6. Package for Fedora

Create:

- `.desktop` launcher;
- app icon;
- RPM spec file;
- dependency list.

## 7. Open-source publication

Before publication:

- remove real customer IPs from examples;
- replace real names with generic sample data;
- add license;
- add contribution guidelines;
- add security policy.
