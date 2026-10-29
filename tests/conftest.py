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
