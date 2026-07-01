# Development Environment

## Fedora setup

```bash
sudo dnf install python3 python3-pip python3-gobject gtk4 libadwaita openfortivpn
```

## Virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Run tests

```bash
pytest
```

## Run CLI

```bash
vpn-doctor --version
vpn-doctor profiles
vpn-doctor diagnose
```
