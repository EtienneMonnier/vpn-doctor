import os
import stat

import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Never let tests read the developer's real VPN profiles."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture(autouse=True)
def isolated_networkmanager(tmp_path, monkeypatch):
    """Hide the developer's real NetworkManager connections behind an empty nmcli.

    Tests that need NetworkManager install their own fake nmcli in front of it.
    """
    bin_dir = tmp_path / "isolated-bin"
    bin_dir.mkdir()
    for tool in ("nmcli", "journalctl"):
        fake = bin_dir / tool
        fake.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return bin_dir


class FakeKeyring:
    """In-memory stand-in for the desktop keyring."""

    def __init__(self):
        self.secrets = {}
        self.available = True

    def lookup(self, profile, kind):
        return self.secrets.get((profile.name, kind))

    def store(self, profile, kind, value):
        self.secrets[(profile.name, kind)] = value
        return True

    def forget(self, profile):
        self.secrets = {key: v for key, v in self.secrets.items() if key[0] != profile.name}


@pytest.fixture(autouse=True)
def fake_keyring(monkeypatch):
    """Never let tests read or write the developer's real keyring."""
    keyring = FakeKeyring()
    monkeypatch.setattr("vpn_doctor.core.controller.KeyringSecretStore", lambda: keyring)
    return keyring
