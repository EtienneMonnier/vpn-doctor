# CLI Specification

The CLI exists for early development, testing and advanced users.

## Current commands

```bash
vpn-doctor --version
vpn-doctor profiles
vpn-doctor diagnose
```

## Future commands

```bash
vpn-doctor profile list
vpn-doctor profile show <id>
vpn-doctor diagnose <profile>
vpn-doctor connect <profile>
vpn-doctor disconnect
vpn-doctor report export --format markdown
```

## Rule

CLI output should be readable first and machine-readable later through explicit
`--json` options.
