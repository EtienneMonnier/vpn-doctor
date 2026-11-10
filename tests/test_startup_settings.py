from vpn_doctor.core.controller import ApplicationController
from vpn_doctor.models.profile import VPNProfile


def controller_with(profiles):
    controller = ApplicationController()
    controller._profile_cache = profiles
    return controller


OFFICE = VPNProfile(name="Office", backend="networkmanager", nm_uuid="1111", vpn_type="openvpn")
FORTI = VPNProfile(name="Forti", backend="openfortivpn", host="vpn.example.com", port=443)


def test_default_connection_is_selected_at_startup():
    ApplicationController().set_default_connection("Forti")

    controller = controller_with([OFFICE, FORTI])

    assert controller.default_profile().name == "Forti"


def test_autoconnect_needs_a_default_connection():
    controller = controller_with([OFFICE, FORTI])
    controller.set_autoconnect(True)
    assert controller.startup_connection() is None

    controller.set_default_connection("Office")
    assert controller.startup_connection() == OFFICE

    controller.set_autoconnect(False)
    assert controller.startup_connection() is None


def test_unknown_default_connection_is_ignored():
    ApplicationController().set_default_connection("Deleted VPN")
    controller = controller_with([OFFICE, FORTI])
    controller.set_autoconnect(True)

    assert controller.default_profile() == OFFICE
    assert controller.startup_connection() is None


def test_connection_editor_command(monkeypatch):
    controller = controller_with([OFFICE, FORTI])
    monkeypatch.setattr("vpn_doctor.core.controller.shutil.which", lambda name: f"/usr/bin/{name}")

    assert controller.connection_editor_command() == ["nm-connection-editor", "--create", "--type=vpn"]
    assert controller.connection_editor_command(OFFICE) == ["nm-connection-editor", "--edit=1111"]
