"""GTK4/libadwaita main window.

The module imports GTK lazily inside `run_ui()` so CLI tests and non-GNOME
environments can import vpn_doctor without requiring PyGObject at import time.

Threading rule: backend callbacks (log lines) arrive on a reader thread and
blocking work (diagnostics, disconnect) runs on worker threads. Every widget
update goes back to the GTK main loop through `GLib.idle_add`.
"""

from __future__ import annotations

import logging
import threading
import time

from vpn_doctor.backend.errors import BackendError
from vpn_doctor.core.controller import ApplicationController
from vpn_doctor.i18n import _
from vpn_doctor.ui.view_models import ConnectionStatusViewModel, ConnectionTimer

LOGGER = logging.getLogger(__name__)

STATUS_REFRESH_MS = 500
STATUS_CSS_CLASSES = ("success", "warning", "error")


def run_ui() -> int:
    """Launch the GTK UI."""
    try:
        import gi  # type: ignore
    except ImportError:
        print("GTK dependencies are not installed. Install python3-gobject, gtk4 and libadwaita.")
        return 1

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")

    from gi.repository import Adw, GLib, Gtk  # type: ignore

    controller = ApplicationController()

    class VPNDoctorWindow(Adw.ApplicationWindow):
        def __init__(self, app: Adw.Application) -> None:
            super().__init__(application=app)
            self.set_title("VPN Doctor")
            self.set_default_size(760, 560)

            self.timer = ConnectionTimer()
            self.busy = False

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

            tagline = Gtk.Label(label=_("Diagnose. Connect. Protect."))
            tagline.add_css_class("dim-label")
            tagline.set_halign(Gtk.Align.START)

            profile = controller.default_profile()
            profile_label = Gtk.Label(
                label=_("Profile: {name} ({host}:{port})").format(
                    name=profile.name, host=profile.host, port=profile.port
                )
            )
            profile_label.set_halign(Gtk.Align.START)

            status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            self.status_label = Gtk.Label(label=_("Disconnected"))
            self.status_label.add_css_class("title-2")
            self.timer_label = Gtk.Label(label="")
            self.timer_label.add_css_class("numeric")
            self.timer_label.add_css_class("dim-label")
            status_box.append(self.status_label)
            status_box.append(self.timer_label)

            self.subtitle_label = Gtk.Label(label=_("VPN is not connected"))
            self.subtitle_label.set_halign(Gtk.Align.START)
            self.subtitle_label.set_wrap(True)
            self.subtitle_label.set_xalign(0)

            button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

            self.connect_button = Gtk.Button(label=_("Connect"))
            self.connect_button.add_css_class("suggested-action")
            self.connect_button.connect("clicked", self.on_connect_clicked)

            self.disconnect_button = Gtk.Button(label=_("Disconnect"))
            self.disconnect_button.add_css_class("destructive-action")
            self.disconnect_button.connect("clicked", self.on_disconnect_clicked)

            self.diagnose_button = Gtk.Button(label=_("Diagnose"))
            self.diagnose_button.connect("clicked", self.on_diagnose_clicked)

            button_box.append(self.connect_button)
            button_box.append(self.disconnect_button)
            button_box.append(self.diagnose_button)

            self.log_view = Gtk.TextView()
            self.log_view.set_editable(False)
            self.log_view.set_cursor_visible(False)
            self.log_view.set_monospace(True)
            self.log_buffer = self.log_view.get_buffer()

            self.scroller = Gtk.ScrolledWindow()
            self.scroller.set_child(self.log_view)
            self.scroller.set_vexpand(True)

            root.append(title)
            root.append(tagline)
            root.append(profile_label)
            root.append(status_box)
            root.append(self.subtitle_label)
            root.append(button_box)
            root.append(self.scroller)

            toolbar_view.set_content(root)
            self.set_content(toolbar_view)

            self.refresh_status()
            GLib.timeout_add(STATUS_REFRESH_MS, self.refresh_status)

        def append_log(self, message: str) -> bool:
            end_iter = self.log_buffer.get_end_iter()
            self.log_buffer.insert(end_iter, message + "\n")
            adjustment = self.scroller.get_vadjustment()
            adjustment.set_value(adjustment.get_upper())
            return GLib.SOURCE_REMOVE

        def append_log_from_thread(self, message: str) -> None:
            GLib.idle_add(self.append_log, message)

        def refresh_status(self) -> bool:
            status = controller.current_status()
            view_model = ConnectionStatusViewModel.from_status(status)

            self.status_label.set_label(view_model.title)
            self.subtitle_label.set_label(view_model.subtitle)
            for css_class in STATUS_CSS_CLASSES:
                self.status_label.remove_css_class(css_class)
            if view_model.css_class in STATUS_CSS_CLASSES:
                self.status_label.add_css_class(view_model.css_class)

            elapsed = self.timer.update(status.state, time.monotonic())
            self.timer_label.set_label(elapsed or "")

            self.connect_button.set_sensitive(view_model.can_connect and not self.busy)
            self.disconnect_button.set_sensitive(view_model.can_disconnect and not self.busy)
            self.diagnose_button.set_sensitive(not self.busy)
            return GLib.SOURCE_CONTINUE

        def run_in_background(self, work, on_done) -> None:
            """Run blocking work off the main loop, then call on_done(result)."""
            self.busy = True
            self.refresh_status()

            def worker() -> None:
                try:
                    result = work()
                except Exception as exc:  # reported to the user in the log view
                    LOGGER.exception("Background UI task failed")
                    result = exc
                GLib.idle_add(finish, result)

            def finish(result) -> bool:
                self.busy = False
                on_done(result)
                self.refresh_status()
                return GLib.SOURCE_REMOVE

            threading.Thread(target=worker, daemon=True).start()

        def on_connect_clicked(self, _button: Gtk.Button) -> None:
            entry = Gtk.PasswordEntry()
            entry.set_show_peek_icon(True)
            entry.set_property("activates-default", True)

            dialog = Adw.AlertDialog(
                heading=_("VPN password"),
                body=_("The password is sent to openfortivpn and never stored."),
            )
            dialog.set_extra_child(entry)
            dialog.add_response("cancel", _("Cancel"))
            dialog.add_response("connect", _("Connect"))
            dialog.set_response_appearance("connect", Adw.ResponseAppearance.SUGGESTED)
            dialog.set_default_response("connect")
            dialog.set_close_response("cancel")
            dialog.connect("response", self.on_password_response, entry)
            dialog.present(self)

        def on_password_response(self, _dialog, response: str, entry) -> None:
            password = entry.get_text()
            entry.set_text("")
            if response != "connect":
                return

            self.append_log(_("Starting connection…"))
            try:
                controller.start_connection(password, on_log=self.append_log_from_thread)
            except BackendError as exc:
                self.append_log(_("Could not start the VPN backend: {error}").format(error=exc))
            self.refresh_status()

        def on_disconnect_clicked(self, _button: Gtk.Button) -> None:
            self.append_log(_("Stopping connection…"))

            def done(result) -> None:
                if isinstance(result, Exception):
                    self.append_log(_("Disconnect failed: {error}").format(error=result))
                else:
                    self.append_log(_("Disconnected"))

            self.run_in_background(controller.stop_connection, done)

        def on_diagnose_clicked(self, _button: Gtk.Button) -> None:
            self.append_log(_("Running diagnostics…"))

            def done(result) -> None:
                if isinstance(result, Exception):
                    self.append_log(_("Diagnostics failed: {error}").format(error=result))
                    return
                self.append_log(result.summary)
                for item in result.items:
                    icon = "OK" if item.success else "FAIL"
                    self.append_log(f"[{icon}] {item.name}: {item.message}")
                    if item.suggestion:
                        self.append_log("      " + _("Suggestion: {text}").format(text=item.suggestion))

            self.run_in_background(controller.diagnose_default_profile, done)

    class VPNDoctorGtkApplication(Adw.Application):
        def __init__(self) -> None:
            super().__init__(application_id="io.github.vpndoctor.VPNDoctor")

        def do_activate(self) -> None:
            window = VPNDoctorWindow(self)
            window.present()

        def do_shutdown(self) -> None:
            # Never leave a VPN tunnel running behind a closed window.
            if controller.current_status().state != "disconnected":
                controller.stop_connection()
            Adw.Application.do_shutdown(self)

    app = VPNDoctorGtkApplication()
    return app.run([])
