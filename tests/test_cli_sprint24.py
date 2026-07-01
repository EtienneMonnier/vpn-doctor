from vpn_doctor.app import main


def test_gui_command_handles_missing_gtk(monkeypatch, capsys):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "gi":
            raise ImportError("missing gi")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    result = main(["gui"])
    captured = capsys.readouterr()

    assert result == 1
    assert "GTK dependencies are not installed" in captured.out
