"""GTK4/libadwaita main window skeleton.

The module imports GTK lazily inside `run_ui()` so CLI tests and non-GNOME
environments can import vpn_doctor without requiring PyGObject at import time.
"""

from __future__ import annotations

from vpn_doctor.core.controller import ApplicationController
from vpn_doctor.models.status import VPNStatus
from vpn_doctor.ui.view_models import ConnectionStatusViewModel


def run_ui() -> int:
    """Launch the experimental GTK UI.

    This is the first UI milestone. It is intentionally read-only and safe:
    it displays status and offers buttons, but real connect/disconnect wiring
    will be completed in the next sprint.
    """
    try:
        import gi  # type: ignore
    except ImportError:
        print("GTK dependencies are not installed. Install python3-gobject, gtk4 and libadwaita.")
        return 1

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")

    from gi.repository import Adw, Gtk  # type: ignore

    controller = ApplicationController()

    class VPNDoctorWindow(Adw.ApplicationWindow):
        def __init__(self, app: Adw.Application) -> None:
            super().__init__(application=app)
            self.set_title("VPN Doctor")
            self.set_default_size(760, 520)

            toolbar_view = Adw.ToolbarView()
            header = Adw.HeaderBar()
            toolbar_view.add_top_bar(header)

            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            root.set_margin_top(24)
            root.set_margin_bottom(24)
            root.set_margin_start(24)
            root.set_margin_end(24)

            title = Gtk.Label(label="VPN Doctor")
            title.add_css_class("title-1")
            title.set_halign(Gtk.Align.START)

            tagline = Gtk.Label(label="Diagnose. Connect. Protect.")
            tagline.add_css_class("dim-label")
            tagline.set_halign(Gtk.Align.START)

            self.status_label = Gtk.Label(label="Disconnected")
            self.status_label.add_css_class("title-2")
            self.status_label.set_halign(Gtk.Align.START)

            self.subtitle_label = Gtk.Label(label="VPN is not connected")
            self.subtitle_label.set_halign(Gtk.Align.START)
            self.subtitle_label.add_css_class("dim-label")

            button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

            self.connect_button = Gtk.Button(label="Connect")
            self.connect_button.add_css_class("suggested-action")
            self.connect_button.connect("clicked", self.on_connect_clicked)

            self.disconnect_button = Gtk.Button(label="Disconnect")
            self.disconnect_button.add_css_class("destructive-action")
            self.disconnect_button.connect("clicked", self.on_disconnect_clicked)

            button_box.append(self.connect_button)
            button_box.append(self.disconnect_button)

            self.log_view = Gtk.TextView()
            self.log_view.set_editable(False)
            self.log_view.set_monospace(True)
            self.log_buffer = self.log_view.get_buffer()

            scroller = Gtk.ScrolledWindow()
            scroller.set_child(self.log_view)
            scroller.set_vexpand(True)

            root.append(title)
            root.append(tagline)
            root.append(self.status_label)
            root.append(self.subtitle_label)
            root.append(button_box)
            root.append(scroller)

            toolbar_view.set_content(root)
            self.set_content(toolbar_view)

            self.refresh_status()

        def append_log(self, message: str) -> None:
            end_iter = self.log_buffer.get_end_iter()
            self.log_buffer.insert(end_iter, message + "\\n")

        def refresh_status(self) -> None:
            profile = controller.settings.load_default_profile()
            status: VPNStatus = controller.backend_manager.status(profile)
            view_model = ConnectionStatusViewModel.from_status(status)

            self.status_label.set_label(view_model.title)
            self.subtitle_label.set_label(view_model.subtitle)
            self.connect_button.set_sensitive(view_model.can_connect)
            self.disconnect_button.set_sensitive(view_model.can_disconnect)

        def on_connect_clicked(self, _button: Gtk.Button) -> None:
            self.append_log("Connect clicked. Real UI connection wiring is planned for Sprint 2.5.")
            self.refresh_status()

        def on_disconnect_clicked(self, _button: Gtk.Button) -> None:
            self.append_log("Disconnect clicked. Real UI disconnection wiring is planned for Sprint 2.5.")
            self.refresh_status()

    class VPNDoctorGtkApplication(Adw.Application):
        def __init__(self) -> None:
            super().__init__(application_id="io.github.vpndoctor.VPNDoctor")

        def do_activate(self) -> None:
            window = VPNDoctorWindow(self)
            window.present()

    app = VPNDoctorGtkApplication()
    return app.run([])
