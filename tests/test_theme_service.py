from vpn_doctor.services.settings_service import SettingsService
from vpn_doctor.services.theme_service import ThemeService


def test_builtin_skins_are_listed_default_first(tmp_path):
    themes = ThemeService(user_dir=tmp_path / "none").themes()

    assert themes[0].id == "default"
    assert "wasteland" in [theme.id for theme in themes]


def test_wasteland_metadata():
    theme = ThemeService().get("wasteland")

    assert theme.name == "Wasteland Terminal"
    assert theme.color_scheme == "dark"
    assert theme.title.startswith("VPN-DOCTOR")
    assert "#45ee8a" in theme.css()


def test_user_skin_is_discovered_and_overrides_builtin(tmp_path):
    user_dir = tmp_path / "themes"
    user_dir.mkdir()
    (user_dir / "neon.css").write_text(
        "/*\n * @name: Neon Night\n * @color-scheme: dark\n */\n.vd-title { color: #ff00ff; }\n",
        encoding="utf-8",
    )
    (user_dir / "wasteland.css").write_text("/* @name: My Wasteland */\n", encoding="utf-8")

    service = ThemeService(user_dir=user_dir)
    themes = {theme.id: theme for theme in service.themes()}

    assert themes["neon"].name == "Neon Night"
    assert themes["neon"].builtin is False
    assert themes["wasteland"].name == "My Wasteland"


def test_unknown_skin_falls_back_to_default(tmp_path):
    assert ThemeService(user_dir=tmp_path).get("does-not-exist").id == "default"


def test_skin_choice_is_persisted(tmp_path):
    settings = SettingsService(settings_path=tmp_path / "settings.json")

    settings.save_setting("theme", "wasteland")

    assert SettingsService(settings_path=tmp_path / "settings.json").load_settings() == {
        "theme": "wasteland"
    }


def test_skin_logo_resolution(tmp_path):
    from vpn_doctor.services.theme_service import DEFAULT_LOGO

    user_dir = tmp_path / "themes"
    user_dir.mkdir()
    (user_dir / "mine.css").write_text("/* @logo: mine.svg */\n", encoding="utf-8")
    (user_dir / "mine.svg").write_text("<svg/>", encoding="utf-8")
    (user_dir / "escape.css").write_text("/* @logo: ../../etc/passwd */\n", encoding="utf-8")
    service = ThemeService(user_dir=user_dir)

    assert service.get("mine").logo_path == user_dir / "mine.svg"
    assert service.get("wasteland").logo_path.name == "logo-wasteland.svg"
    assert service.get("default").logo_path == DEFAULT_LOGO
    assert service.get("escape").logo_path == DEFAULT_LOGO
