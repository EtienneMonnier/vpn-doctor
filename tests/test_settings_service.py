import json

from vpn_doctor.services.settings_service import SettingsService


def test_settings_service_loads_demo_profile_when_missing(tmp_path):
    service = SettingsService(profile_path=tmp_path / "missing.json")
    profile = service.load_default_profile()

    assert profile.backend == "openfortivpn"
    assert profile.host == "vpn.example.com"


def test_settings_service_loads_json_profiles(tmp_path):
    path = tmp_path / "profiles.json"
    path.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "name": "Test",
                        "backend": "openfortivpn",
                        "host": "vpn.test.local",
                        "port": 44443,
                        "username": "tester",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    service = SettingsService(profile_path=path)
    profile = service.load_default_profile()

    assert profile.name == "Test"
    assert profile.host == "vpn.test.local"
    assert profile.port == 44443
