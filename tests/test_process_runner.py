import subprocess
import time

from vpn_doctor.backend.process_runner import ProcessRunner


class _RootOwnedProcess:
    pid = 4242

    def __init__(self):
        self.waited = False

    def poll(self):
        return None

    def terminate(self):
        raise PermissionError("Operation not permitted")

    def wait(self, timeout=None):
        self.waited = True
        return 0


def test_terminate_uses_privilege_command_for_root_process(monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda argv, **kwargs: calls.append(argv))

    process = _RootOwnedProcess()
    runner = ProcessRunner(process=process)

    runner.terminate(privilege_command=("pkexec",))

    assert calls == [["pkexec", "kill", "-TERM", "4242"]]
    assert process.waited is True
    assert runner.process is None


def test_terminate_stops_real_process():
    runner = ProcessRunner()
    runner.start(["sleep", "30"])

    runner.terminate(timeout=2.0)

    assert runner.process is None


def test_prompt_without_newline_is_reported_and_answered():
    lines, prompts = [], []
    runner = ProcessRunner()
    script = 'printf "INFO:   Connected to gateway.\\nToken: "; read token; echo "got $token"'

    runner.start(["sh", "-c", script], on_line=lines.append, on_prompt=prompts.append, stdin_text="")
    deadline = time.monotonic() + 5
    while not prompts and time.monotonic() < deadline:
        time.sleep(0.02)
    runner.write_stdin("123456\n")
    runner.process.wait(timeout=5)
    runner._reader_thread.join(timeout=5)

    assert prompts == ["Token: "]
    assert lines == ["INFO:   Connected to gateway.", "got 123456"]
