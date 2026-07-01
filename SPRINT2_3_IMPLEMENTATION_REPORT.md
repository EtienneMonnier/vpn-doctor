# Sprint 2.3 Implementation Report

## Summary

Sprint 2.3 adds the first real connection execution path for OpenFortiVPN while
keeping secrets out of the repository.

## Added

- `vpn-doctor connect --wait`
- `vpn-doctor connect --timeout <seconds>`
- Environment-based temporary secret provider
- Profile loading from `~/.config/vpn-doctor/profiles.json`
- Real-time log forwarding through the CLI
- Wait-until-connected/failed/timeout lifecycle helper
- Additional tests for settings, secrets, waiting, and CLI behavior

## Safe usage

Dry-run remains the recommended default validation command:

```bash
vpn-doctor connect --dry-run
```

For a real local test, create a local profile file outside Git:

```bash
mkdir -p ~/.config/vpn-doctor
nano ~/.config/vpn-doctor/profiles.json
```

Example:

```json
{
  "profiles": [
    {
      "name": "My VPN",
      "backend": "openfortivpn",
      "host": "vpn.example.com",
      "port": 443,
      "username": "my-user",
      "trusted_cert": "sha256-hash-if-needed"
    }
  ]
}
```

Then run:

```bash
export VPN_DOCTOR_PASSWORD='your-password'
vpn-doctor connect --wait --timeout 60
```

Do not commit real profiles, passwords, certificates or customer data.

## Next Sprint

Sprint 2.4 should improve runtime persistence, PID management and prepare the
GTK/libadwaita UI integration.

## Validation

Tests executed in pack generation: see `SPRINT2_3_TEST_RESULT.txt`.
