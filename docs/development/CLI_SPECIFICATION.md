# CLI Specification

The CLI serves advanced users, scripts and AI agents. The GTK UI uses the same
controller.

## Commands

```bash
vpn-doctor --version
vpn-doctor profiles
vpn-doctor status [--profile NAME]
vpn-doctor diagnose [--profile NAME]
vpn-doctor connect [--profile NAME] [--dry-run] [--wait] [--timeout SECONDS]
vpn-doctor disconnect [--profile NAME]
vpn-doctor conflicts
vpn-doctor rdp HOST [--port PORT] [--log FILE|-]
vpn-doctor gateways
vpn-doctor approve-gateway [--profile NAME]
vpn-doctor revoke-gateway HOST:PORT
vpn-doctor forget-secrets [--profile NAME]
vpn-doctor gui
```

Without `--profile`, commands act on the default connection chosen in
Preferences, or on the first one.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | success; for `connect --wait`, the tunnel is connected |
| `1` | a check failed, a conflict exists, or an action failed |
| `2` | bad argument: unknown profile, malformed `HOST:PORT`, unreadable log |

## JSON output

Every command except `gui` accepts `--json`, before or after the command
(`vpn-doctor --json status` or `vpn-doctor status --json`). The command then
prints exactly one JSON object on stdout, in UTF-8, and keeps the exit codes
above. Argument syntax errors still come from argparse, as text on stderr.

The schema is stable within a minor version: fields may be added, never
renamed or removed. Optional values are `null`, never missing.

JSON output never contains secrets, user names or certificate paths. It
contains connection names and gateway addresses; `connect` also returns the
backend log, which may name the user: sanitize it before sharing it.

### Shared objects

`Status`:

```json
{
  "backend": "networkmanager",
  "state": "connected",
  "message": null,
  "suggestion": null,
  "prompt": null,
  "vpn_ip": "192.0.2.10",
  "connected_seconds": 42
}
```

`state` is one of `disconnected`, `connecting`, `authenticating`,
`negotiating`, `connected`, `disconnecting`, `failed`, `unknown`. `prompt` is
a question the backend waits for (e.g. a one-time code).

`Report`:

```json
{
  "summary": "1 problem found",
  "success": false,
  "items": [
    {
      "name": "Gateway",
      "success": false,
      "severity": "error",
      "message": "vpn.example.com does not answer on port 443",
      "suggestion": "Check the address and your Internet connection"
    }
  ]
}
```

`severity` is `info`, `warning` or `error`. `suggestion` may be `null`.

### Per command

| Command | Object |
| --- | --- |
| `--version` | `{"version"}` |
| `profiles` | `{"profiles": [{"name", "backend", "managed_by", "vpn_type", "host", "port"}]}` |
| `status` | `{"profile", "status": Status}` |
| `diagnose` | `{"profile", "report": Report}` |
| `conflicts` | `{"report": Report}` (no item: no conflict) |
| `rdp` | `{"host", "port", "probe": Report, "log_analysis": Report or null}` |
| `connect --dry-run` | `{"profile", "command": [...]}` |
| `connect --wait` | `{"profile", "status": Status, "logs": [...]}` |
| `connect` | `{"profile", "started": true, "logs": [...]}` |
| `disconnect` | `{"profile", "disconnected": true}` |
| `gateways` | `{"enforced", "gateways": [{"host", "port", "trusted_cert"}]}` |
| `approve-gateway`, `revoke-gateway` | `{"success", "message"}` |
| `forget-secrets` | `{"success", "message", "profile"}` |
| any error | `{"error"}`, plus `logs` when `connect` failed to start |

In `profiles`, `managed_by` is `networkmanager` or `vpn-doctor` (direct
openfortivpn profile); `vpn_type` is the NetworkManager VPN type (`openvpn`,
`wireguard`, …) or `null`; `host` and `port` are `null` for NetworkManager
connections.

`connect` never asks anything on the terminal, with or without `--json`:
passwords come from `VPN_DOCTOR_PASSWORD`, the keyring or NetworkManager's own agent.
