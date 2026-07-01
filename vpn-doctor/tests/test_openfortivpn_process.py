from __future__ import annotations

from io import StringIO

from vpn_doctor.backend.openfortivpn_process import OpenFortiVPNProcess
from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.models.status import VPNConnectionState


class FakeProcess:
    def __init__(self, lines: list[str] | None = None, exit_code: int = 0) -> None:
        self.pid = 123
        self.stdout = StringIO("\n".join(lines or []) + "\n")
        self._exit_code = exit_code
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return self._exit_code if self.terminated else None

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True
        self.terminated = True

    def wait(self, timeout: float | None = None) -> int:
        return self._exit_code


class FakeRunner:
    def __init__(self, process: FakeProcess) -> None:
        self.process = process
        self.started_argv = None
        self.stdin_text = None

    def start(self, argv, stdin_text=None):
        self.started_argv = list(argv)
        self.stdin_text = stdin_text
        return self.process


def test_openfortivpn_process_dry_run() -> None:
    process = OpenFortiVPNProcess()
    profile = VPNProfile(name="demo", backend="openfortivpn", host="vpn.example.com", port=443)

    status = process.start(["openfortivpn", "vpn.example.com:443"], profile, dry_run=True)

    assert status.state == VPNConnectionState.DISCONNECTED
    assert "Dry run" in status.message


def test_openfortivpn_process_tracks_connected_state() -> None:
    fake = FakeProcess(["INFO:   Tunnel is up and running."])
    runner = FakeRunner(fake)
    process = OpenFortiVPNProcess(runner=runner)
    profile = VPNProfile(name="demo", backend="openfortivpn", host="vpn.example.com", port=443)

    status = process.start(
        ["openfortivpn", "vpn.example.com:443"],
        profile,
        password="secret",
        foreground=False,
    )

    assert status.state == VPNConnectionState.CONNECTING
    assert runner.stdin_text == "secret\n"

    process.handle_log_line("INFO:   Tunnel is up and running.")

    assert process.status.state == VPNConnectionState.CONNECTED


def test_openfortivpn_process_stop() -> None:
    fake = FakeProcess()
    runner = FakeRunner(fake)
    process = OpenFortiVPNProcess(runner=runner)
    profile = VPNProfile(name="demo", backend="openfortivpn", host="vpn.example.com", port=443)

    process.start(["openfortivpn", "vpn.example.com:443"], profile)
    status = process.stop()

    assert fake.terminated is True
    assert status.state == VPNConnectionState.DISCONNECTED
