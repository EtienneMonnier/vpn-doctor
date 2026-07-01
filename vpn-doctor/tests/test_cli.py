from vpn_doctor.core.controller import ApplicationController


def test_version_command(capsys) -> None:
    result = ApplicationController().run(["--version"])

    captured = capsys.readouterr()

    assert result == 0
    assert "VPN Doctor" in captured.out
