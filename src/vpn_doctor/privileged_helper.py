#!/usr/bin/python3 -I
"""VPN Doctor privileged helper.

Installed as /usr/libexec/vpn-doctor/vpn-doctor-helper and started by VPN
Doctor through `pkexec`, under the polkit action io.github.vpndoctor.helper.
It is the only part of VPN Doctor that runs as root. See ADR-0012.

Protocol (stdin, one JSON line, then the bytes for openfortivpn):

    {"host": "vpn.example.com", "port": 443, "username": "demo-user", ...}\\n
    <VPN password>\\n
    <answers to later prompts, e.g. the PEM pass phrase>\\n

The helper trusts nothing it receives:

- it accepts only the profile fields below and builds the openfortivpn
  command itself, from validated values;
- it runs only /usr/bin/openfortivpn, with `-c /dev/null`;
- certificate and key files must be regular PEM files owned by the calling
  user (PKEXEC_UID), or owned by root under /etc/openfortivpn/; the helper
  opens them itself, checks what it opened, and hands the open descriptor to
  openfortivpn (/dev/fd/N), so swapping a path after the check has no effect;
- it stays the parent of openfortivpn and stops it when its stdin is closed:
  VPN Doctor disconnects by closing the pipe, without a second polkit prompt,
  and a crashed VPN Doctor never leaves a tunnel behind.

Standard library only: this file must not import anything from a location
the user can write to.
"""

from __future__ import annotations

import json
import os
import re
import signal
import stat
import subprocess
import sys
import threading

OPENFORTIVPN = "/usr/bin/openfortivpn"
STDBUF = "/usr/bin/stdbuf"
MAX_REQUEST_BYTES = 8192
STOP_TIMEOUT_SECONDS = 10
SAFE_ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8"}

ALLOWED_FIELDS = {"host", "port", "username", "trusted_cert", "realm", "user_cert", "user_key"}
HOST = re.compile(r"^(?=.{1,253}$)[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?$|^[0-9A-Fa-f:.]{2,45}$")
FINGERPRINT = re.compile(r"^[0-9A-Fa-f]{64}$")
TEXT = re.compile(r"^[^\s\x00-\x1f\x7f-][^\x00-\x1f\x7f]{0,255}$")
PEM_MAGIC = b"-----BEGIN "
ROOT_PEM_DIR = "/etc/openfortivpn/"


class InvalidRequest(ValueError):
    """The request is refused; the message says why, without secrets."""


def read_request_line(fd: int = 0) -> bytes:
    """Read exactly one line from fd, byte by byte, so nothing after it is consumed."""
    data = bytearray()
    while len(data) <= MAX_REQUEST_BYTES:
        byte = os.read(fd, 1)
        if not byte:
            raise InvalidRequest("missing request")
        if byte == b"\n":
            return bytes(data)
        data += byte
    raise InvalidRequest("request too long")


def open_pem_file(path: str, caller_uid: int) -> int:
    """Open a PEM file the caller may use and return the open descriptor.

    Checks are made on the opened file (fstat), not on the path, so the path
    cannot be swapped between the check and its use.
    """
    if not isinstance(path, str) or not path.startswith("/") or "\x00" in path:
        raise InvalidRequest("certificate and key paths must be absolute")
    real = os.path.realpath(path)
    try:
        fd = os.open(real, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as exc:
        raise InvalidRequest(f"cannot read {path}") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise InvalidRequest(f"{path} is not a regular file")
        owned_by_caller = info.st_uid == caller_uid
        root_vpn_file = info.st_uid == 0 and real.startswith(ROOT_PEM_DIR)
        if not (owned_by_caller or root_vpn_file):
            raise InvalidRequest(f"{path} must belong to you, or to root under {ROOT_PEM_DIR}")
        if PEM_MAGIC not in os.pread(fd, 4096, 0):
            raise InvalidRequest(f"{path} is not a PEM file")
    except BaseException:
        os.close(fd)
        raise
    return fd


def build_command(request: dict, caller_uid: int, open_fds: list[int] | None = None) -> list[str]:
    """Validate the request and build the openfortivpn command.

    Descriptors opened for certificate and key files are appended to open_fds;
    the caller passes them to openfortivpn.
    """
    open_fds = open_fds if open_fds is not None else []
    if not isinstance(request, dict):
        raise InvalidRequest("the request must be a JSON object")
    unknown = set(request) - ALLOWED_FIELDS
    if unknown:
        raise InvalidRequest(f"unknown fields: {', '.join(sorted(unknown))}")

    host = request.get("host")
    if not isinstance(host, str) or not HOST.match(host):
        raise InvalidRequest("invalid host")
    port = request.get("port")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise InvalidRequest("invalid port")

    command = [OPENFORTIVPN, f"{host}:{port}", "-c", "/dev/null"]

    for field, option in (("username", "-u"), ("realm", "--realm")):
        value = request.get(field)
        if value is None:
            continue
        if not isinstance(value, str) or not TEXT.match(value):
            raise InvalidRequest(f"invalid {field}")
        command += [option, value]

    fingerprint = request.get("trusted_cert")
    if fingerprint is not None:
        if not isinstance(fingerprint, str) or not FINGERPRINT.match(fingerprint):
            raise InvalidRequest("trusted_cert must be a SHA-256 fingerprint (64 hex characters)")
        command += ["--trusted-cert", fingerprint.lower()]

    for field, option in (("user_cert", "--user-cert"), ("user_key", "--user-key")):
        value = request.get(field)
        if value is not None:
            fd = open_pem_file(value, caller_uid)
            open_fds.append(fd)
            command += [option, f"/dev/fd/{fd}"]

    if os.path.exists(STDBUF):
        # Line-buffered output, so VPN Doctor sees each log line at once.
        command = [STDBUF, "-oL", "-eL", *command]
    return command


def caller_uid() -> int:
    """The user who ran pkexec; refuse to run outside pkexec."""
    raw = os.environ.get("PKEXEC_UID", "")
    if not raw.isdigit():
        raise InvalidRequest("must be started through pkexec")
    return int(raw)


def supervise(command: list[str], pass_fds: list[int]) -> int:
    """Run openfortivpn, feed it our stdin, stop it when stdin closes."""
    child = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        env=SAFE_ENV,
        close_fds=True,
        pass_fds=tuple(pass_fds),
    )
    stopping = threading.Event()

    def stop(*_args) -> None:
        if stopping.is_set():
            return
        stopping.set()
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=STOP_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                child.kill()

    def pump() -> None:
        try:
            while chunk := os.read(0, 4096):
                child.stdin.write(chunk)
                child.stdin.flush()
        except (BrokenPipeError, OSError):
            pass
        # VPN Doctor closed the pipe (disconnect, crash or exit): stop the tunnel.
        stop()

    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, stop)
    threading.Thread(target=pump, daemon=True).start()
    return child.wait()


def main(argv: list[str]) -> int:
    if argv[1:] != ["connect"]:
        print("usage: vpn-doctor-helper connect  (request on stdin)", file=sys.stderr)
        return 2
    open_fds: list[int] = []
    try:
        uid = caller_uid()
        request = json.loads(read_request_line().decode("utf-8"))
        command = build_command(request, uid, open_fds)
    except (InvalidRequest, ValueError, UnicodeDecodeError) as exc:
        for fd in open_fds:
            os.close(fd)
        print(f"ERROR:  vpn-doctor-helper refused the request: {exc}", file=sys.stderr, flush=True)
        return 2
    return supervise(command, open_fds)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
