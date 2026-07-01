# Sprint 1 Core Files

Copy the `src/` directory into the root of the VPN Doctor repository.

Recommended commands from the project root:

```bash
git checkout dev
git pull
git checkout -b feature/sprint1-core

cp -r /path/to/generated/src/* src/

python -m pip install -e .
vpn-doctor --version
vpn-doctor profiles
vpn-doctor diagnose

git add .
git commit -m "feat: add Sprint 1 core foundation"
git push -u origin feature/sprint1-core
```

Notes:

- The OpenFortiVPN backend only performs safe diagnostics for now.
- Real connection/disconnection will be implemented in Sprint 2.
- No real VPN data or secrets are included.
