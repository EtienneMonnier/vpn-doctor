import os
import stat
import time

import pytest

from vpn_doctor.backend.log_parser import OpenFortiVPNLogParser, ParsedLogKind
from vpn_doctor.core.controller import ApplicationController
from vpn_doctor.models.status import VPNConnectionState
from vpn_doctor.services.secret_service import SecretKind, classify_prompt
from vpn_doctor.services.settings_service import SettingsService

FAKE_PEM_PROMPT = """#!/bin/sh
read password
echo "VPN account password: "
printf "Enter PEM pass phrase: "
read passphrase
if [ "$password" = "vpn-secret" ] && [ "$passphrase" = "pem-secret" ]; then
    echo "INFO:   Tunnel is up and running."
    sleep 30
else
    echo "ERROR:  SSL_CTX_use_PrivateKey_file: bad decrypt"
fi
"""


@pytest.mark.parametrize(
    ("prompt", "kind"),
    [
        ("VPN account password: ", SecretKind.PASSWORD),
        ("Enter PEM pass phrase: ", SecretKind.PEM_PASSPHRASE),
        ("Two-factor authentication token: ", None),
        ("Please enter one-time password: ", None),
        ("Continue? ", None),
    ],
)
def test_classify_prompt(prompt, kind):
    assert classify_prompt(prompt) == kind


def test_parser_reports_private_key_error():
    parsed = OpenFortiVPNLogParser().parse("ERROR:  SSL_CTX_use_PrivateKey_file: bad decrypt")
    assert parsed.kind == ParsedLogKind.PRIVATE_KEY_ERROR


@pytest.fixture
def controller(tmp_path, monkeypatch):
    fake = tmp_path / "bin" / "openfortivpn"
    fake.parent.mkdir()
    fake.write_text(FAKE_PEM_PROMPT, encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{fake.parent}{os.pathsep}{os.environ['PATH']}")

    controller = ApplicationController()
    controller.settings = SettingsService(profile_path=tmp_path / "missing.json")
    backend = controller.backend_manager.registry.get("openfortivpn")
    backend.process.privilege_command = ()
    backend.process.output_wrapper = ()
    yield controller
    controller.stop_connection()


def _wait(controller, predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and not predicate(controller.current_status()):
        time.sleep(0.05)
    return controller.current_status()


def test_pem_prompt_is_asked_then_remembered(controller, fake_keyring):
    controller.start_connection("vpn-secret", on_log=lambda line: None, remember=True)
    status = _wait(controller, lambda s: s.prompt is not None)
    assert status.prompt == "Enter PEM pass phrase:"

    controller.answer_prompt("pem-secret", remember=True)
    status = _wait(controller, lambda s: s.state == VPNConnectionState.CONNECTED)

    assert status.state == VPNConnectionState.CONNECTED
    assert set(fake_keyring.secrets.values()) == {"vpn-secret", "pem-secret"}


def test_remembered_secrets_connect_without_any_prompt(controller, fake_keyring):
    profile = controller.default_profile()
    fake_keyring.store(profile, SecretKind.PASSWORD, "vpn-secret")
    fake_keyring.store(profile, SecretKind.PEM_PASSPHRASE, "pem-secret")
    logs = []

    controller.start_connection(controller.stored_password(), on_log=logs.append)
    status = _wait(controller, lambda s: s.state == VPNConnectionState.CONNECTED)

    assert status.state == VPNConnectionState.CONNECTED
    assert "(answered from the keyring)" in logs
    assert not any("pem-secret" in line or "vpn-secret" in line for line in logs)


def test_wrong_remembered_passphrase_is_explained(controller, fake_keyring):
    fake_keyring.store(controller.default_profile(), SecretKind.PEM_PASSPHRASE, "stale")

    controller.start_connection("vpn-secret", on_log=lambda line: None)
    status = _wait(controller, lambda s: s.state == VPNConnectionState.FAILED)

    assert status.state == VPNConnectionState.FAILED
    assert "forget the saved secrets" in status.suggestion


def test_one_time_codes_are_never_remembered(fake_keyring):
    controller = ApplicationController()

    assert controller.can_remember("Two-factor authentication token: ") is False
    assert controller.can_remember("Enter PEM pass phrase: ") is True


def test_forget_secrets(capsys, fake_keyring):
    controller = ApplicationController()
    profile = controller.default_profile()
    fake_keyring.store(profile, SecretKind.PASSWORD, "vpn-secret")

    assert controller.run(["forget-secrets"]) == 0
    assert fake_keyring.secrets == {}
    assert "Secrets forgotten" in capsys.readouterr().out


def test_forget_secrets_reports_unreachable_keyring(capsys, fake_keyring):
    fake_keyring.available = False

    assert ApplicationController().run(["forget-secrets"]) == 1
    assert "not reachable" in capsys.readouterr().out
