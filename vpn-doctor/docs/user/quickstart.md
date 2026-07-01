# Quickstart

VPN Doctor is not ready for end users yet.

For developers:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
vpn-doctor --version
vpn-doctor profiles
vpn-doctor diagnose
```

The default profile is a placeholder and is expected to fail gateway reachability.
