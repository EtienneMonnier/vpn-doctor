from vpn_doctor.app import main


def test_status_command(capsys):
    result = main(["status"])
    captured = capsys.readouterr()

    assert result == 0
    assert "openfortivpn" in captured.out


def test_connect_dry_run(capsys):
    result = main(["connect", "--dry-run"])
    captured = capsys.readouterr()

    assert result == 0
    assert "openfortivpn" in captured.out
    assert "vpn.example.com:443" in captured.out
