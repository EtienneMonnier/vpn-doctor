"""GTK4/libadwaita main window.

The module imports GTK lazily inside `run_ui()` so CLI tests and non-GNOME
environments can import vpn_doctor without requiring PyGObject at import time.

Layout: one tab per connection (several VPNs can run at once), a banner for
conflicts between them, and a main menu (☰).

Threading rule: backend callbacks (log lines) arrive on reader threads and
blocking work (diagnostics, disconnect, conflict checks) runs on worker
threads. Every widget update goes back to the GTK main loop through
`GLib.idle_add`.

Skins: widgets carry `vd-*` CSS classes documented in
docs/development/THEMES.md. A skin is a CSS file applied at user priority.
"""

from __future__ import annotations

import logging
import threading
import time

from vpn_doctor import __version__
from vpn_doctor.backend.errors import BackendError
from vpn_doctor.core.controller import ApplicationController
from vpn_doctor.i18n import _
from vpn_doctor.models.status import VPNConnectionState
from vpn_doctor.services.theme_service import BUILTIN_ASSET_DIR
from vpn_doctor.ui.view_models import ConnectionStatusViewModel, ConnectionTimer, boot_lines

LOGGER = logging.getLogger(__name__)

STATUS_REFRESH_MS = 500
CONFLICT_REFRESH_MS = 5000
STATE_CSS_CLASSES = ("vd-success", "vd-warning", "vd-error", "vd-neutral")
DEFAULT_TITLE = "VPN Doctor"
DEFAULT_TAGLINE = "Diagnose. Connect. Protect."
APP_ID = "io.github.vpndoctor.VPNDoctor"
BOOT_LINE_MS = 220
BOOT_HOLD_MS = 500
TAB_MARKS = {
    VPNConnectionState.CONNECTED: "●",
    VPNConnectionState.FAILED: "✕",
}


def run_in_background(work, on_done) -> None:
    """Run blocking work off the main loop, then call on_done(result) on it."""
    from gi.repository import GLib  # type: ignore

    def worker() -> None:
        try:
            result = work()
        except Exception as exc:  # reported to the user in the log view
            LOGGER.exception("Background UI task failed")
            result = exc

        def finish() -> bool:
            on_done(result)
            return GLib.SOURCE_REMOVE

        GLib.idle_add(finish)

    threading.Thread(target=worker, daemon=True).start()


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

    def secret_dialog(parent, heading, body, accept, on_answer, can_remember=False) -> None:
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
        dialog.present(parent)

    class ConnectionPanel(Gtk.Box):
        """Status, details, actions and log of one connection."""

        def __init__(self, window, profile) -> None:
            super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            self.window = window
            self.profile = profile
            self.timer = ConnectionTimer()
            self.busy = False
            self.asked_prompt: str | None = None
            self.state = VPNConnectionState.DISCONNECTED

            panels = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16, homogeneous=True)
            panels.append(self.build_status_card())
            panels.append(self.build_connection_card())
            self.append(panels)
            self.append(self.build_log_card())
            self.refresh()

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
            box.append(label(_("■ CONNECTION"), "vd-section-title"))
            box.append(label(self.profile.name, "vd-connection-name"))

            profile = self.profile
            gateway = f"{profile.host}:{profile.port}" if profile.port else profile.host
            details = (
                (_("TYPE"), profile.vpn_type or profile.backend),
                (_("GATEWAY"), gateway or "—"),
                (_("MANAGED BY"), "NetworkManager" if profile.nm_uuid else "VPN Doctor"),
            )
            meta = Gtk.Grid(column_spacing=16, row_spacing=4)
            for row, (key, value) in enumerate(details):
                meta.attach(label(key, "vd-meta-key"), 0, row, 1, 1)
                value_label = label(value, "vd-meta-value")
                value_label.set_ellipsize(Pango.EllipsizeMode.END)
                value_label.set_hexpand(True)
                meta.attach(value_label, 1, row, 1, 1)
            box.append(meta)

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

        # -- status ----------------------------------------------------------------

        def append_log(self, message: str) -> bool:
            end_iter = self.log_buffer.get_end_iter()
            self.log_buffer.insert(end_iter, message + "\n")
            adjustment = self.scroller.get_vadjustment()
            adjustment.set_value(adjustment.get_upper())
            return GLib.SOURCE_REMOVE

        def append_log_from_thread(self, message: str) -> None:
            GLib.idle_add(self.append_log, message)

        def refresh(self) -> None:
            status = controller.current_status(self.profile)
            self.state = status.state
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

            if status.prompt != self.asked_prompt:
                self.asked_prompt = status.prompt
                if status.prompt:
                    self.ask_prompt(status.prompt)

        def run_busy(self, work, on_done) -> None:
            self.busy = True
            self.refresh()

            def done(result) -> None:
                self.busy = False
                on_done(result)
                self.refresh()

            run_in_background(work, done)

        # -- actions -----------------------------------------------------------------

        def ask_prompt(self, prompt: str) -> None:
            """Ask the user to answer a backend prompt, e.g. a two-factor token."""

            def on_answer(answer: str | None, remember: bool) -> None:
                if answer is None:
                    self.on_disconnect_clicked(None)
                    return
                try:
                    controller.answer_prompt(answer, remember=remember, profile=self.profile)
                except BackendError as exc:
                    self.append_log(_("Could not send the answer: {error}").format(error=exc))
                self.refresh()

            secret_dialog(
                self.window,
                _("{name} asks for more information").format(name=self.profile.name),
                prompt,
                _("Send"),
                on_answer,
                can_remember=controller.can_remember(prompt),
            )

        def on_connect_clicked(self, _button) -> None:
            if not controller.requires_password(self.profile):
                # NetworkManager asks for secrets through the GNOME secret agent.
                self.start_connection(None)
                return

            stored = controller.stored_password(self.profile)
            if stored is not None:
                self.append_log(_("Using the password remembered in the keyring"))
                self.start_connection(stored)
                return

            def on_answer(password: str | None, remember: bool) -> None:
                if password is not None:
                    self.start_connection(password, remember=remember)

            secret_dialog(
                self.window,
                _("VPN password for {name}").format(name=self.profile.name),
                _("The password is sent to openfortivpn through stdin, never written to a file."),
                _("Connect"),
                on_answer,
                can_remember=controller.can_remember(),
            )

        def start_connection(self, password: str | None, remember: bool = False) -> None:
            self.append_log(_("Connecting {name}…").format(name=self.profile.name))
            try:
                controller.start_connection(
                    password,
                    on_log=self.append_log_from_thread,
                    remember=remember,
                    profile=self.profile,
                )
            except BackendError as exc:
                self.append_log(_("Could not start the VPN backend: {error}").format(error=exc))
            self.refresh()

        def on_disconnect_clicked(self, _button) -> None:
            self.append_log(_("Stopping connection…"))

            def done(result) -> None:
                if isinstance(result, Exception):
                    self.append_log(_("Disconnect failed: {error}").format(error=result))
                else:
                    self.append_log(_("Disconnected"))

            self.run_busy(lambda: controller.stop_connection(self.profile), done)

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

            self.run_busy(lambda: controller.diagnose_default_profile(self.profile), done)

    class VPNDoctorWindow(Adw.ApplicationWindow):
        def __init__(self, app: Adw.Application) -> None:
            super().__init__(application=app)
            self.set_title("VPN Doctor")
            self.set_default_size(960, 680)
            self.add_css_class("vd-window")

            self.css_provider: Gtk.CssProvider | None = None
            self.conflicts = []
            self.checking_conflicts = False

            Gtk.IconTheme.get_for_display(self.get_display()).add_search_path(
                str(BUILTIN_ASSET_DIR / "icons")
            )
            self.set_icon_name(APP_ID)

            toolbar_view = Adw.ToolbarView()
            header = Adw.HeaderBar()
            header.pack_end(self.build_main_menu())
            toolbar_view.add_top_bar(header)

            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            root.set_margin_top(20)
            root.set_margin_bottom(20)
            root.set_margin_start(20)
            root.set_margin_end(20)

            heading = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
            # Gtk.Image, not Gtk.Picture: it keeps a fixed size for any SVG.
            self.header_logo = Gtk.Image(pixel_size=56)
            self.header_logo.add_css_class("vd-header-logo")
            titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            titles.set_valign(Gtk.Align.CENTER)
            self.title_label = label(DEFAULT_TITLE, "vd-title")
            self.tagline_label = label(_(DEFAULT_TAGLINE), "vd-tagline")
            titles.append(self.title_label)
            titles.append(self.tagline_label)
            heading.append(self.header_logo)
            heading.append(titles)
            root.append(heading)

            self.banner = Adw.Banner()
            self.banner.add_css_class("vd-conflict-banner")
            self.banner.set_button_label(_("Show"))
            self.banner.connect("button-clicked", lambda _banner: self.show_conflicts())
            root.append(self.banner)

            self.tab_view = Adw.TabView()
            self.tab_view.set_vexpand(True)
            self.tab_view.connect("notify::selected-page", self.on_tab_selected)
            self.tab_view.connect("close-page", self.on_close_page)

            tab_bar = Adw.TabBar(view=self.tab_view)
            tab_bar.set_autohide(False)
            tab_bar.add_css_class("vd-tabs")
            self.open_menu_button = Gtk.MenuButton(label="+")
            self.open_menu_button.set_tooltip_text(_("Open a connection"))
            self.open_menu_button.add_css_class("vd-open-button")
            tab_bar.set_end_action_widget(self.open_menu_button)

            root.append(tab_bar)
            root.append(self.tab_view)

            self.stack = Gtk.Stack()
            self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
            self.stack.set_transition_duration(400)
            self.stack.add_named(self.build_boot_page(), "boot")
            self.stack.add_named(root, "main")
            toolbar_view.set_content(self.stack)
            self.set_content(toolbar_view)

            self.apply_theme(controller.current_theme())
            self.populate_open_menu()
            self.open_initial_tabs()
            if controller.boot_animation_enabled():
                self.start_boot_animation()
            else:
                self.stack.set_visible_child_name("main")
            GLib.timeout_add(STATUS_REFRESH_MS, self.refresh_tabs)
            GLib.timeout_add(CONFLICT_REFRESH_MS, self.check_conflicts)

        # -- startup animation -----------------------------------------------------

        def build_boot_page(self) -> Gtk.Widget:
            page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
            page.add_css_class("vd-boot")
            page.set_valign(Gtk.Align.CENTER)
            page.set_halign(Gtk.Align.CENTER)

            self.boot_logo = Gtk.Image(pixel_size=220)
            self.boot_log = label("", "vd-boot-log")
            self.boot_log.set_size_request(420, -1)
            hint = label(_("Click or press a key to skip"), "vd-boot-hint", xalign=0.5)

            page.append(self.boot_logo)
            page.append(self.boot_log)
            page.append(hint)

            click = Gtk.GestureClick()
            click.connect("pressed", lambda *_args: self.finish_boot())
            page.add_controller(click)
            keys = Gtk.EventControllerKey()
            keys.connect("key-pressed", lambda *_args: self.finish_boot() or True)
            self.add_controller(keys)
            return page

        def start_boot_animation(self) -> None:
            report = controller.boot_report()
            self.boot_pending = boot_lines(
                __version__,
                report["connections"],
                report["networkmanager"],
                report["keyring"],
            )
            self.boot_shown: list[str] = []
            self.stack.set_visible_child_name("boot")
            GLib.timeout_add(BOOT_LINE_MS, self.type_boot_line)

        def type_boot_line(self) -> bool:
            if self.stack.get_visible_child_name() != "boot":
                return GLib.SOURCE_REMOVE
            if not self.boot_pending:
                GLib.timeout_add(BOOT_HOLD_MS, lambda: self.finish_boot() or GLib.SOURCE_REMOVE)
                return GLib.SOURCE_REMOVE
            self.boot_shown.append("> " + self.boot_pending.pop(0))
            self.boot_log.set_label("\n".join(self.boot_shown))
            return GLib.SOURCE_CONTINUE

        def finish_boot(self) -> None:
            if self.stack.get_visible_child_name() == "boot":
                self.stack.set_visible_child_name("main")

        # -- preferences and about ------------------------------------------------

        def show_preferences(self) -> None:
            dialog = Adw.PreferencesDialog()
            page = Adw.PreferencesPage(title=_("General"), icon_name="preferences-system-symbolic")
            dialog.add(page)

            appearance = Adw.PreferencesGroup(title=_("Appearance"))
            page.add(appearance)

            themes = controller.themes()
            names = Gtk.StringList()
            for theme in themes:
                names.append(theme.name + ("" if theme.builtin else _(" (custom)")))
            skin_row = Adw.ComboRow(title=_("Skin"), model=names)
            current = controller.current_theme().id
            skin_row.set_selected(next((i for i, t in enumerate(themes) if t.id == current), 0))

            def on_skin(row, _param) -> None:
                theme = controller.set_theme(themes[row.get_selected()].id)
                self.apply_theme(theme)

            skin_row.connect("notify::selected", on_skin)
            appearance.add(skin_row)

            skins_folder = Adw.ActionRow(
                title=_("Custom skins"),
                subtitle=_("Drop CSS files in {path}").format(path=controller.theme_service.user_dir),
            )
            for text, callback in ((_("Open folder"), self.open_skins_folder), (_("Reload"), self.reload_skins)):
                button = Gtk.Button(label=text, valign=Gtk.Align.CENTER)
                button.connect("clicked", lambda _button, callback=callback: callback())
                skins_folder.add_suffix(button)
            appearance.add(skins_folder)

            boot_row = Adw.SwitchRow(
                title=_("Startup animation"),
                subtitle=_("Logo and boot checks when VPN Doctor starts"),
            )
            boot_row.set_active(controller.boot_animation_enabled())
            boot_row.connect(
                "notify::active", lambda row, _param: controller.set_boot_animation(row.get_active())
            )
            appearance.add(boot_row)

            secrets = Adw.PreferencesGroup(
                title=_("Saved secrets"),
                description=_(
                    "Passwords and PEM pass phrases of openfortivpn profiles, kept in the "
                    "desktop keyring. NetworkManager connections keep theirs in GNOME Settings."
                ),
            )
            page.add(secrets)
            for profile in controller.direct_profiles():
                row = Adw.ActionRow(title=profile.name, subtitle=profile.host)
                button = Gtk.Button(label=_("Forget"), valign=Gtk.Align.CENTER)
                button.add_css_class("destructive-action")

                def forget(button, profile=profile) -> None:
                    if controller.forget_secrets(profile):
                        button.set_label(_("Forgotten"))
                        button.set_sensitive(False)

                button.connect("clicked", forget)
                row.add_suffix(button)
                secrets.add(row)

            dialog.present(self)

        def show_about(self) -> None:
            about = Adw.AboutDialog(
                application_name="VPN Doctor",
                application_icon=APP_ID,
                version=__version__,
                developer_name="Etienne Monnier",
                comments=_("Linux VPN troubleshooting assistant.\nDiagnose. Connect. Protect."),
                website="https://github.com/EtienneMonnier/vpn-doctor",
                license_type=Gtk.License.MIT_X11,
            )
            about.present(self)

        # -- tabs ----------------------------------------------------------------

        def panels(self) -> list[ConnectionPanel]:
            pages = self.tab_view.get_pages()
            return [pages.get_item(i).get_child() for i in range(pages.get_n_items())]

        def open_tab(self, profile, select: bool = True) -> ConnectionPanel:
            for panel in self.panels():
                if panel.profile.name == profile.name:
                    if select:
                        self.tab_view.set_selected_page(self.tab_view.get_page(panel))
                    return panel
            panel = ConnectionPanel(self, profile)
            page = self.tab_view.append(panel)
            page.set_title(profile.name)
            if select:
                self.tab_view.set_selected_page(page)
            return panel

        def open_initial_tabs(self) -> None:
            """Open the selected connection, plus every connection already active."""
            self.open_tab(controller.default_profile())
            for profile in controller.profiles():
                if controller.current_status(profile).state == VPNConnectionState.CONNECTED:
                    self.open_tab(profile, select=False)
            self.check_conflicts()

        def on_tab_selected(self, *_args) -> None:
            page = self.tab_view.get_selected_page()
            if page is not None:
                controller.select_profile(page.get_child().profile.name)

        def on_close_page(self, tab_view, page) -> bool:
            # Keep one tab. Closing a tab never disconnects: reopen it with "+".
            tab_view.close_page_finish(page, tab_view.get_n_pages() > 1)
            return True  # handled here

        def refresh_tabs(self) -> bool:
            for panel in self.panels():
                panel.refresh()
                page = self.tab_view.get_page(panel)
                mark = TAB_MARKS.get(panel.state, "○")
                page.set_title(f"{mark} {panel.profile.name}")
                page.set_loading(
                    panel.state in {VPNConnectionState.CONNECTING, VPNConnectionState.AUTHENTICATING}
                )
            return GLib.SOURCE_CONTINUE

        def populate_open_menu(self) -> None:
            menu = Gio.Menu()
            connections = Gio.Menu()
            for profile in controller.profiles():
                kind = profile.vpn_type or profile.backend
                item = Gio.MenuItem.new(f"{profile.name} ({kind})", None)
                item.set_action_and_target_value(
                    "win.open-tab", GLib.Variant.new_string(profile.name)
                )
                connections.append_item(item)
            menu.append_section(_("Connections"), connections)
            tools = Gio.Menu()
            tools.append(_("Reload connections"), "win.reload-connections")
            menu.append_section(None, tools)
            self.open_menu_button.set_menu_model(menu)

        # -- conflicts -----------------------------------------------------------

        def check_conflicts(self) -> bool:
            if not self.checking_conflicts:
                self.checking_conflicts = True

                def done(result) -> None:
                    self.checking_conflicts = False
                    self.conflicts = [] if isinstance(result, Exception) else result
                    count = len(self.conflicts)
                    if count:
                        self.banner.set_title(
                            _("⚠ {count} network conflict(s): {first}").format(
                                count=count, first=self.conflicts[0].name
                            )
                        )
                    self.banner.set_revealed(count > 0)

                run_in_background(controller.network_conflicts, done)
            return GLib.SOURCE_CONTINUE

        def show_conflicts(self) -> None:
            body = "\n\n".join(
                f"{item.name}\n{item.message}\n→ {item.suggestion}" for item in self.conflicts
            )
            dialog = Adw.AlertDialog(heading=_("Network conflicts"), body=body)
            dialog.add_response("close", _("Close"))
            dialog.present(self)

        # -- main menu -----------------------------------------------------------

        def build_main_menu(self) -> Gtk.MenuButton:
            open_tab = Gio.SimpleAction.new("open-tab", GLib.VariantType.new("s"))
            open_tab.connect("activate", self.on_open_tab)
            self.add_action(open_tab)

            simple_actions = {
                "preferences": self.show_preferences,
                "about": self.show_about,
                "reload-skins": self.reload_skins,
                "open-skins-folder": self.open_skins_folder,
                "forget-secrets": self.forget_secrets,
                "reload-connections": self.reload_connections,
            }
            for name, callback in simple_actions.items():
                action = Gio.SimpleAction.new(name, None)
                action.connect("activate", lambda *_args, callback=callback: callback())
                self.add_action(action)

            # Text, not an icon: icon themes may draw icons in full color.
            self.menu_button = Gtk.MenuButton(label="☰")
            self.menu_button.add_css_class("vd-menu-button")
            self.menu_button.set_tooltip_text(_("Main menu"))
            self.populate_main_menu()
            return self.menu_button

        def populate_main_menu(self) -> None:
            menu = Gio.Menu()
            main = Gio.Menu()
            main.append(_("Preferences"), "win.preferences")
            main.append(_("Forget saved secrets of this connection"), "win.forget-secrets")
            menu.append_section(None, main)
            about = Gio.Menu()
            about.append(_("About VPN Doctor"), "win.about")
            menu.append_section(None, about)
            self.menu_button.set_menu_model(menu)

        def on_open_tab(self, _action, value) -> None:
            controller.select_profile(value.get_string())
            self.open_tab(controller.default_profile())

        def reload_connections(self) -> None:
            controller.reload_profiles()
            self.populate_open_menu()

        def current_panel(self) -> ConnectionPanel | None:
            page = self.tab_view.get_selected_page()
            return page.get_child() if page is not None else None

        def forget_secrets(self) -> None:
            panel = self.current_panel()
            if panel is None:
                return
            profile = panel.profile
            if profile.nm_uuid is not None:
                panel.append_log(
                    _("{name} is managed by NetworkManager: edit its secrets in GNOME Settings.").format(
                        name=profile.name
                    )
                )
            elif controller.forget_secrets(profile):
                panel.append_log(_("Saved secrets forgotten for {name}").format(name=profile.name))
            else:
                panel.append_log(_("The keyring is not reachable"))

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
            for image in (self.header_logo, self.boot_logo):
                image.set_from_file(str(theme.logo_path))

        def on_css_error(self, _provider, section, error, theme_name: str) -> None:
            location = section.get_start_location()
            message = _("Skin {name}, line {line}: {error}").format(
                name=theme_name, line=location.lines + 1, error=error.message
            )
            LOGGER.warning(message)
            panel = self.current_panel() if hasattr(self, "tab_view") else None
            if panel is not None:
                panel.append_log(message)

        def reload_skins(self) -> None:
            self.apply_theme(controller.current_theme())

        def open_skins_folder(self) -> None:
            folder = controller.theme_service.user_dir
            folder.mkdir(parents=True, exist_ok=True)
            Gio.AppInfo.launch_default_for_uri(folder.as_uri(), None)

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
