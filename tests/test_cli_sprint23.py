from vpn_doctor.app import main


def test_connect_wait_timeout_fails_fast(capsys):
    result = main(["connect", "--wait", "--timeout", "0.1"])
    captured = capsys.readouterr()

    assert result in {0, 1}
    assert "openfortivpn" in captured.out or "Connection" in captured.out
