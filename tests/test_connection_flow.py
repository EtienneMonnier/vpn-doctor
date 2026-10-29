"""End-to-end connection flow with a fake openfortivpn executable."""

import os
import stat
import time

from vpn_doctor.core.controller import ApplicationController
from vpn_doctor.models.status import VPNConnectionState
from vpn_doctor.services.settings_service import SettingsService

FAKE_WRONG_PASSWORD = """#!/bin/sh
read password
echo "INFO:   Connected to gateway."
echo "ERROR:  Could not authenticate to gateway. Please check the password, client certificate, etc."
echo "INFO:   Closed connection to gateway."
exit 1
"""


def _install_fake_openfortivpn(tmp_path, monkeypatch, script):
    fake = tmp_path / "openfortivpn"
    fake.write_text(script, encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")


def _wait_for_state(controller, states, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = controller.current_status()
        if status.state in states:
            return status
        time.sleep(0.05)
    return controller.current_status()


def test_wrong_password_is_explained(tmp_path, monkeypatch):
    _install_fake_openfortivpn(tmp_path, monkeypatch, FAKE_WRONG_PASSWORD)
    controller = ApplicationController()
    controller.settings = SettingsService(profile_path=tmp_path / "missing.json")
    controller.backend_manager.registry.get("openfortivpn").process.privilege_command = ()
    logs = []

    controller.start_connection("not-the-password", on_log=logs.append)
    status = _wait_for_state(controller, {VPNConnectionState.FAILED})

    assert status.state == VPNConnectionState.FAILED
    assert "password" in status.suggestion
    assert not any("not-the-password" in line for line in logs)
