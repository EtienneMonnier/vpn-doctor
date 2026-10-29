from vpn_doctor.core.controller import ApplicationController
from vpn_doctor.services.settings_service import SettingsService


def test_profiles_command_lists_demo_profile(tmp_path, capsys):
    controller = ApplicationController()
    controller.settings = SettingsService(profile_path=tmp_path / "missing.json")

    result = controller.run(["profiles"])

    assert result == 0
    assert "Demo Fortinet VPN (openfortivpn)" in capsys.readouterr().out
