"""GTK4/libadwaita main window.

The module imports GTK lazily inside `run_ui()` so CLI tests and non-GNOME
environments can import vpn_doctor without requiring PyGObject at import time.

Threading rule: backend callbacks (log lines) arrive on reader threads and
blocking work (diagnostics, disconnect) runs on worker threads. Every widget
update goes back to the GTK main loop through `GLib.idle_add`.

Skins: widgets carry `vd-*` CSS classes documented in
docs/development/THEMES.md. A skin is a CSS file applied at user priority.
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
STATE_CSS_CLASSES = ("vd-success", "vd-warning", "vd-error", "vd-neutral")
DEFAULT_TITLE = "VPN Doctor"
DEFAULT_TAGLINE = "Diagnose. Connect. Protect."


def run_ui() -> int:
    """Launch the GTK UI."""
    try:
        import gi  # type: ignore
    except ImportError:
        print("GTK dependencies are not installed. Install python3-gobject, gtk4 and libadwaita.")
        return 1

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")

    from gi.repository import Adw, Gio, GLib, Gtk, Pango  # type: ignore

    controller = ApplicationController()

    def label(text: str, *css_classes: str, xalign: float = 0.0) -> Gtk.Label:
        widget = Gtk.Label(label=text, xalign=xalign)
        for css_class in css_classes:
            widget.add_css_class(css_class)
        return widget

    def card(*css_classes: str) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.add_css_class("card")
        box.add_css_class("vd-card")
        for css_class in css_classes:
            box.add_css_class(css_class)
        return box

    class VPNDoctorWindow(Adw.ApplicationWindow):
        def __init__(self, app: Adw.Application) -> None:
            super().__init__(application=app)
            self.set_title("VPN Doctor")
            self.set_default_size(920, 640)
            self.add_css_class("vd-window")

            self.timer = ConnectionTimer()
            self.busy = False
            self.asked_prompt: str | None = None
            self.css_provider: Gtk.CssProvider | None = None

            toolbar_view = Adw.ToolbarView()
            header = Adw.HeaderBar()
            header.pack_end(self.build_skin_menu())
            toolbar_view.add_top_bar(header)

            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            root.set_margin_top(20)
            root.set_margin_bottom(20)
            root.set_margin_start(20)
            root.set_margin_end(20)

            self.title_label = label(DEFAULT_TITLE, "vd-title")
            self.tagline_label = label(_(DEFAULT_TAGLINE), "vd-tagline")
            root.append(self.title_label)
            root.append(self.tagline_label)

            panels = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16, homogeneous=True)
            panels.set_vexpand(False)
            panels.append(self.build_status_card())
            panels.append(self.build_connection_card())
            root.append(panels)
            root.append(self.build_log_card())

            toolbar_view.set_content(root)
            self.set_content(toolbar_view)

            self.apply_theme(controller.current_theme())
            self.refresh_profiles()
            self.refresh_status()
            GLib.timeout_add(STATUS_REFRESH_MS, self.refresh_status)

        # -- layout -------------------------------------------------------------

        def build_status_card(self) -> Gtk.Box:
            self.status_card = card("vd-status-card")

            top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            section = label(_("■ STATUS"), "vd-section-title")
            section.set_hexpand(True)
            self.pill_label = label("", "vd-pill", xalign=0.5)
            self.pill_label.set_valign(Gtk.Align.CENTER)
            top.append(section)
            top.append(self.pill_label)

            middle = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            self.status_label = label(_("Disconnected"), "vd-state")
            self.status_label.set_hexpand(True)
            self.timer_label = label("--:--:--", "vd-timer", "numeric", xalign=1.0)
            middle.append(self.status_label)
            middle.append(self.timer_label)

            self.subtitle_label = label("", "vd-subtitle")
            self.subtitle_label.set_wrap(True)

            self.status_card.append(top)
            self.status_card.append(middle)
            self.status_card.append(self.subtitle_label)
            return self.status_card

        def build_connection_card(self) -> Gtk.Box:
            box = card("vd-connection-card")

            top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            section = label(_("■ CONNECTION"), "vd-section-title")
            section.set_hexpand(True)
            # Text, not icons: icon themes may draw them in full color.
            reload_button = Gtk.Button(label="↻")
            reload_button.set_tooltip_text(_("Reload connections"))
            reload_button.add_css_class("flat")
            reload_button.connect("clicked", lambda _button: self.refresh_profiles(reload=True))
            top.append(section)
            top.append(reload_button)

            self.profile_model = Gtk.StringList()
            self.profile_dropdown = Gtk.DropDown(model=self.profile_model)
            self.profile_dropdown.add_css_class("vd-profile")
            self.profile_dropdown.connect("notify::selected", self.on_profile_selected)

            meta = Gtk.Grid(column_spacing=16, row_spacing=4)
            self.meta_values = {}
            for row, key in enumerate((_("TYPE"), _("GATEWAY"), _("MANAGED BY"))):
                meta.attach(label(key, "vd-meta-key"), 0, row, 1, 1)
                value = label("—", "vd-meta-value")
                value.set_ellipsize(Pango.EllipsizeMode.END)
                value.set_hexpand(True)
                meta.attach(value, 1, row, 1, 1)
                self.meta_values[key] = value

            buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, homogeneous=True)
            self.connect_button = Gtk.Button(label=_("Connect"))
            self.connect_button.add_css_class("suggested-action")
            self.connect_button.add_css_class("vd-primary")
            self.connect_button.connect("clicked", self.on_connect_clicked)

            self.disconnect_button = Gtk.Button(label=_("Disconnect"))
            self.disconnect_button.add_css_class("vd-danger")
            self.disconnect_button.connect("clicked", self.on_disconnect_clicked)

            self.diagnose_button = Gtk.Button(label=_("Diagnose"))
            self.diagnose_button.add_css_class("vd-secondary")
            self.diagnose_button.connect("clicked", self.on_diagnose_clicked)

            for button in (self.connect_button, self.disconnect_button, self.diagnose_button):
                buttons.append(button)

            box.append(top)
            box.append(self.profile_dropdown)
            box.append(meta)
            box.append(buttons)
            return box

        def build_log_card(self) -> Gtk.Box:
            box = card("vd-log-card")
            box.set_vexpand(True)
            box.append(label(_("■ LOG"), "vd-section-title"))

            self.log_view = Gtk.TextView()
            self.log_view.set_editable(False)
            self.log_view.set_cursor_visible(False)
            self.log_view.set_monospace(True)
            self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            self.log_view.add_css_class("vd-log")
            self.log_buffer = self.log_view.get_buffer()

            self.scroller = Gtk.ScrolledWindow()
            self.scroller.set_child(self.log_view)
            self.scroller.set_vexpand(True)
            box.append(self.scroller)
            return box

        def build_skin_menu(self) -> Gtk.MenuButton:
            initial = GLib.Variant.new_string(controller.current_theme().id)
            action = Gio.SimpleAction.new_stateful("skin", GLib.VariantType.new("s"), initial)
            action.connect("activate", self.on_skin_selected)
            self.add_action(action)

            reload_action = Gio.SimpleAction.new("reload-skins", None)
            reload_action.connect("activate", lambda *_args: self.reload_skins())
            self.add_action(reload_action)

            folder_action = Gio.SimpleAction.new("open-skins-folder", None)
            folder_action.connect("activate", lambda *_args: self.open_skins_folder())
            self.add_action(folder_action)

            self.skin_button = Gtk.MenuButton(label=_("SKIN"))
            self.skin_button.add_css_class("vd-skin-button")
            self.skin_button.set_tooltip_text(_("Skin"))
            self.populate_skin_menu()
            return self.skin_button

        def populate_skin_menu(self) -> None:
            menu = Gio.Menu()
            skins = Gio.Menu()
            for theme in controller.themes():
                suffix = "" if theme.builtin else _(" (custom)")
                skins.append(theme.name + suffix, f"win.skin::{theme.id}")
            menu.append_section(_("Skin"), skins)
            tools = Gio.Menu()
            tools.append(_("Reload skins"), "win.reload-skins")
            tools.append(_("Open skins folder"), "win.open-skins-folder")
            menu.append_section(None, tools)
            self.skin_button.set_menu_model(menu)

        # -- skins ---------------------------------------------------------------

        def apply_theme(self, theme) -> None:
            display = self.get_display()
            if self.css_provider is not None:
                Gtk.StyleContext.remove_provider_for_display(display, self.css_provider)

            provider = Gtk.CssProvider()
            provider.connect("parsing-error", self.on_css_error, theme.name)
            css = theme.css()
            if hasattr(provider, "load_from_string"):
                provider.load_from_string(css)
            else:  # GTK < 4.12
                provider.load_from_data(css, -1)
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
            )
            self.css_provider = provider

            schemes = {
                "dark": Adw.ColorScheme.FORCE_DARK,
                "light": Adw.ColorScheme.FORCE_LIGHT,
                "default": Adw.ColorScheme.DEFAULT,
            }
            Adw.StyleManager.get_default().set_color_scheme(schemes[theme.color_scheme])
            self.title_label.set_label(theme.title or DEFAULT_TITLE)
            self.tagline_label.set_label(theme.tagline or _(DEFAULT_TAGLINE))

        def on_css_error(self, _provider, section, error, theme_name: str) -> None:
            location = section.get_start_location()
            self.append_log(
                _("Skin {name}, line {line}: {error}").format(
                    name=theme_name, line=location.lines + 1, error=error.message
                )
            )

        def on_skin_selected(self, action, value) -> None:
            action.set_state(value)
            self.apply_theme(controller.set_theme(value.get_string()))

        def reload_skins(self) -> None:
            self.populate_skin_menu()
            self.apply_theme(controller.current_theme())
            self.append_log(_("Skins reloaded"))

        def open_skins_folder(self) -> None:
            folder = controller.theme_service.user_dir
            folder.mkdir(parents=True, exist_ok=True)
            Gio.AppInfo.launch_default_for_uri(folder.as_uri(), None)

        # -- profiles ------------------------------------------------------------

        def refresh_profiles(self, reload: bool = False) -> None:
            profiles = controller.reload_profiles() if reload else controller.profiles()
            current = controller.default_profile().name
            self.updating_profiles = True
            self.profile_model.splice(0, self.profile_model.get_n_items(), [p.name for p in profiles])
            names = [p.name for p in profiles]
            self.profile_dropdown.set_selected(names.index(current) if current in names else 0)
            self.updating_profiles = False
            self.show_profile_details()

        def on_profile_selected(self, dropdown, _param) -> None:
            if getattr(self, "updating_profiles", False):
                return
            item = dropdown.get_selected_item()
            if item is not None:
                controller.select_profile(item.get_string())
                self.timer = ConnectionTimer()
                self.show_profile_details()
                self.refresh_status()

        def show_profile_details(self) -> None:
            profile = controller.default_profile()
            gateway = f"{profile.host}:{profile.port}" if profile.port else profile.host
            managed_by = "NetworkManager" if profile.nm_uuid else "VPN Doctor"
            values = (profile.vpn_type or profile.backend, gateway or "—", managed_by)
            for value_label, value in zip(self.meta_values.values(), values, strict=True):
                value_label.set_label(value)

        # -- status ----------------------------------------------------------------

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
            state_class = f"vd-{view_model.css_class}"

            self.status_label.set_label(view_model.title)
            self.subtitle_label.set_label(view_model.subtitle)
            self.pill_label.set_label(view_model.pill)
            for widget in (self.status_label, self.pill_label, self.status_card):
                for css_class in STATE_CSS_CLASSES:
                    widget.remove_css_class(css_class)
                widget.add_css_class(state_class)

            elapsed = self.timer.update(status.state, time.monotonic())
            self.timer_label.set_label(elapsed or "--:--:--")

            self.connect_button.set_sensitive(view_model.can_connect and not self.busy)
            self.disconnect_button.set_sensitive(view_model.can_disconnect and not self.busy)
            self.diagnose_button.set_sensitive(not self.busy)
            self.profile_dropdown.set_sensitive(view_model.can_connect and not self.busy)

            if status.prompt != self.asked_prompt:
                self.asked_prompt = status.prompt
                if status.prompt:
                    self.ask_prompt(status.prompt)
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

        # -- dialogs -----------------------------------------------------------------

        def secret_dialog(
            self,
            heading: str,
            body: str,
            accept: str,
            on_answer,
            can_remember: bool = False,
        ) -> None:
            """Ask for a secret; on_answer(value, remember) gets None on cancel."""
            entry = Gtk.PasswordEntry()
            entry.set_show_peek_icon(True)
            entry.set_property("activates-default", True)

            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            content.append(entry)
            remember = Gtk.CheckButton(label=_("Remember in the keyring"))
            if can_remember:
                content.append(remember)

            dialog = Adw.AlertDialog(heading=heading, body=body)
            dialog.set_extra_child(content)
            dialog.add_response("cancel", _("Cancel"))
            dialog.add_response("accept", accept)
            dialog.set_response_appearance("accept", Adw.ResponseAppearance.SUGGESTED)
            dialog.set_default_response("accept")
            dialog.set_close_response("cancel")

            def on_response(_dialog, response: str) -> None:
                answer = entry.get_text()
                entry.set_text("")
                if response == "accept":
                    on_answer(answer, remember.get_active())
                else:
                    on_answer(None, False)

            dialog.connect("response", on_response)
            dialog.present(self)

        def ask_prompt(self, prompt: str) -> None:
            """Ask the user to answer a backend prompt, e.g. a two-factor token."""

            def on_answer(answer: str | None, remember: bool) -> None:
                if answer is None:
                    self.on_disconnect_clicked(None)
                    return
                try:
                    controller.answer_prompt(answer, remember=remember)
                except BackendError as exc:
                    self.append_log(_("Could not send the answer: {error}").format(error=exc))
                self.refresh_status()

            self.secret_dialog(
                _("The VPN asks for more information"),
                prompt,
                _("Send"),
                on_answer,
                can_remember=controller.can_remember(prompt),
            )

        # -- actions -----------------------------------------------------------------

        def on_connect_clicked(self, _button) -> None:
            if not controller.requires_password():
                # NetworkManager asks for secrets through the GNOME secret agent.
                self.start_connection(None)
                return

            stored = controller.stored_password()
            if stored is not None:
                self.append_log(_("Using the password remembered in the keyring"))
                self.start_connection(stored)
                return

            def on_answer(password: str | None, remember: bool) -> None:
                if password is not None:
                    self.start_connection(password, remember=remember)

            self.secret_dialog(
                _("VPN password"),
                _("The password is sent to openfortivpn through stdin, never written to a file."),
                _("Connect"),
                on_answer,
                can_remember=controller.can_remember(),
            )

        def start_connection(self, password: str | None, remember: bool = False) -> None:
            profile = controller.default_profile()
            self.append_log(_("Connecting {name}…").format(name=profile.name))
            try:
                controller.start_connection(
                    password,
                    on_log=self.append_log_from_thread,
                    remember=remember,
                )
            except BackendError as exc:
                self.append_log(_("Could not start the VPN backend: {error}").format(error=exc))
            self.refresh_status()

        def on_disconnect_clicked(self, _button) -> None:
            self.append_log(_("Stopping connection…"))

            def done(result) -> None:
                if isinstance(result, Exception):
                    self.append_log(_("Disconnect failed: {error}").format(error=result))
                else:
                    self.append_log(_("Disconnected"))

            self.run_in_background(controller.stop_connection, done)

        def on_diagnose_clicked(self, _button) -> None:
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
            controller.stop_unmanaged_connections()
            Adw.Application.do_shutdown(self)

    app = VPNDoctorGtkApplication()
    return app.run([])
