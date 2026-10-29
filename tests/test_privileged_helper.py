import os
import subprocess
import sys
import time

import pytest

from vpn_doctor import privileged_helper as helper
from vpn_doctor.privileged_helper import InvalidRequest, build_command

UID = os.getuid()
FINGERPRINT = "ab" * 32


def command_for(**request):
    request.setdefault("host", "vpn.example.com")
    request.setdefault("port", 443)
    command = build_command(request, UID)
    # stdbuf is optional: compare from openfortivpn onwards.
    return command[command.index(helper.OPENFORTIVPN):]


def test_builds_openfortivpn_command_from_validated_fields():
    assert command_for(username="demo-user", trusted_cert=FINGERPRINT.upper(), realm="staff") == [
        "/usr/bin/openfortivpn",
        "vpn.example.com:443",
        "-c",
        "/dev/null",
        "-u",
        "demo-user",
        "--realm",
        "staff",
        "--trusted-cert",
        FINGERPRINT,
    ]


@pytest.mark.parametrize(
    "request_fields",
    [
        {"host": "vpn.example.com; rm -rf /"},
        {"host": "-c/etc/shadow"},
        {"port": 0},
        {"port": "443"},
        {"port": True},
        {"username": "--pppd-plugin=/tmp/evil.so"},
        {"username": "demo\nuser"},
        {"trusted_cert": "not-a-fingerprint"},
        {"pppd_plugin": "/tmp/evil.so"},
        {"user_key": "relative/key.pem"},
    ],
)
def test_refuses_dangerous_requests(request_fields):
    request = {"host": "vpn.example.com", "port": 443, **request_fields}
    with pytest.raises(InvalidRequest):
        build_command(request, UID)


def test_pem_file_is_passed_as_an_open_descriptor(tmp_path):
    key = tmp_path / "client.pem"
    key.write_text("-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n")
    fds = []

    command = build_command({"host": "vpn.example.com", "port": 443, "user_key": str(key)}, UID, fds)

    assert len(fds) == 1
    assert command[-2:] == ["--user-key", f"/dev/fd/{fds[0]}"]
    assert os.read(fds[0], 10) == b"-----BEGIN"
    os.close(fds[0])


def test_refuses_files_that_are_not_pem(tmp_path):
    secret = tmp_path / "shadow"
    secret.write_text("root:$6$hash:19000:0:99999:7:::\n")
    with pytest.raises(InvalidRequest, match="not a PEM file"):
        build_command({"host": "vpn.example.com", "port": 443, "user_cert": str(secret)}, UID)


def test_refuses_files_of_another_user(tmp_path):
    key = tmp_path / "client.pem"
    key.write_text("-----BEGIN CERTIFICATE-----\n")
    with pytest.raises(InvalidRequest, match="must belong to you"):
        build_command({"host": "vpn.example.com", "port": 443, "user_cert": str(key)}, UID + 1)


def test_refuses_symlink_as_final_component(tmp_path):
    target = tmp_path / "real.pem"
    target.write_text("-----BEGIN CERTIFICATE-----\n")
    link = tmp_path / "link.pem"
    link.symlink_to(target)
    # realpath resolves the link, then O_NOFOLLOW opens the real file only.
    fds = []
    build_command({"host": "vpn.example.com", "port": 443, "user_cert": str(link)}, UID, fds)
    assert os.path.samestat(os.fstat(fds[0]), os.stat(target))
    os.close(fds[0])


def test_read_request_line_leaves_the_rest_for_openfortivpn():
    read_end, write_end = os.pipe()
    os.write(write_end, b'{"host": "x"}\nsecret-password\n')
    os.close(write_end)

    assert helper.read_request_line(read_end) == b'{"host": "x"}'
    assert os.read(read_end, 100) == b"secret-password\n"
    os.close(read_end)


def test_refuses_to_run_outside_pkexec(monkeypatch, capsys):
    monkeypatch.delenv("PKEXEC_UID", raising=False)

    assert helper.main(["vpn-doctor-helper", "connect"]) == 2
    assert "pkexec" in capsys.readouterr().err


def test_stops_openfortivpn_when_stdin_closes(tmp_path):
    fake = tmp_path / "openfortivpn"
    fake.write_text("#!/bin/sh\necho started\nexec sleep 30\n")
    fake.chmod(0o755)
    script = (
        "import sys; from vpn_doctor import privileged_helper as h; "
        f"sys.exit(h.supervise([{str(fake)!r}], []))"
    )
    env = {**os.environ, "PYTHONPATH": "src"}
    process = subprocess.Popen(
        [sys.executable, "-c", script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        env=env,
    )
    assert process.stdout.readline() == b"started\n"
    started = time.monotonic()

    process.stdin.close()  # what VPN Doctor does to disconnect

    assert process.wait(timeout=5) != 0
    assert time.monotonic() - started < 5


