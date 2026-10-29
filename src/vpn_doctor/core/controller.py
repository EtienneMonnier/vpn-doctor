"""Application controller."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from vpn_doctor.backend.errors import BackendProcessError
from vpn_doctor.backend.manager import BackendManager
from vpn_doctor.backend.networkmanager import NetworkManagerBackend
from vpn_doctor.backend.openfortivpn import OpenFortiVPNBackend
from vpn_doctor.backend.openfortivpn_process import OpenFortiVPNProcess
from vpn_doctor.backend.process_runner import line_buffering_command
from vpn_doctor.backend.registry import BackendRegistry
from vpn_doctor.diagnostics.conflicts import collect_snapshot, find_conflicts
from vpn_doctor.diagnostics.rdp import DEFAULT_RDP_PORT, analyze_freerdp_log, probe_rdp
from vpn_doctor.models.diagnostic import DiagnosticItem, DiagnosticReport
from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.models.status import VPNConnectionState, VPNStatus
from vpn_doctor.services.privilege_service import default_privilege_command
from vpn_doctor.services.secret_service import (
    EnvironmentSecretProvider,
    KeyringSecretStore,
    SecretKind,
    classify_prompt,
)
from vpn_doctor.services.settings_service import SettingsService
from vpn_doctor.services.theme_service import Theme, ThemeService


class ApplicationController:
    """High-level application coordinator."""

    def __init__(self) -> None:
        self.settings = SettingsService()
        self.theme_service = ThemeService()
        self.secret_provider = EnvironmentSecretProvider()
        self.keyring = KeyringSecretStore()

        registry = BackendRegistry()
        process = OpenFortiVPNProcess(
            privilege_command=default_privilege_command(),
            output_wrapper=line_buffering_command(),
        )
        registry.register(OpenFortiVPNBackend(process=process))
        registry.register(NetworkManagerBackend())
        self.backend_manager = BackendManager(registry=registry)

        self.selected_profile_name: str | None = None
        self._profile_cache: list[VPNProfile] | None = None

    # Public API used by the GTK UI. The UI never talks to backends directly.

    def profiles(self) -> list[VPNProfile]:
        """NetworkManager connections plus profiles.json, or the demo profile."""
        if self._profile_cache is None:
            found = [
                *self.backend_manager.discovered_profiles(),
                *self.settings.load_configured_profiles(),
            ]
            self._profile_cache = found or [self.settings.demo_profile()]
        return self._profile_cache

    def reload_profiles(self) -> list[VPNProfile]:
        self._profile_cache = None
        return self.profiles()

    def select_profile(self, name: str) -> VPNProfile:
        for profile in self.profiles():
            if profile.name == name:
                self.selected_profile_name = name
                return profile
        raise ValueError(f"Unknown profile: {name}")

    def default_profile(self) -> VPNProfile:
        """Return the selected profile, or the first one."""
        profiles = self.profiles()
        for profile in profiles:
            if profile.name == self.selected_profile_name:
                return profile
        return profiles[0]

    def themes(self) -> list[Theme]:
        return self.theme_service.themes()

    def current_theme(self) -> Theme:
        return self.theme_service.get(self.settings.load_settings().get("theme"))

    def set_theme(self, theme_id: str) -> Theme:
        theme = self.theme_service.get(theme_id)
        self.settings.save_setting("theme", theme.id)
        return theme

    # Every method below acts on `profile`, or on the selected profile.

    def requires_password(self, profile: VPNProfile | None = None) -> bool:
        """False when the backend asks for secrets itself (NetworkManager)."""
        return not self.backend_manager.manages_secrets(profile or self.default_profile())

    def current_status(self, profile: VPNProfile | None = None) -> VPNStatus:
        return self.backend_manager.status(profile or self.default_profile())

    def diagnose_default_profile(self, profile: VPNProfile | None = None) -> DiagnosticReport:
        return self.backend_manager.diagnose(profile or self.default_profile())

    def stored_password(self, profile: VPNProfile | None = None) -> str | None:
        """Return the password remembered in the keyring."""
        return self.keyring.lookup(profile or self.default_profile(), SecretKind.PASSWORD)

    def can_remember(self, prompt: str | None = None) -> bool:
        """True when the keyring works and the prompt asks for a reusable secret."""
        if prompt is not None and classify_prompt(prompt) is None:
            return False
        return self.keyring.available

    def start_connection(
        self,
        password: str | None,
        on_log: Callable[[str], None],
        remember: bool = False,
        profile: VPNProfile | None = None,
    ) -> None:
        """Start a connection without waiting for the tunnel.

        Raises BackendProcessError when the backend process cannot start.
        """
        profile = profile or self.default_profile()
        if password is not None and remember:
            self.keyring.store(profile, SecretKind.PASSWORD, password)
        self.backend_manager.connect(
            profile,
            password=password,
            on_log=on_log,
            prompt_handler=self._keyring_answerer(profile),
        )

    def answer_prompt(
        self,
        answer: str,
        remember: bool = False,
        profile: VPNProfile | None = None,
    ) -> None:
        profile = profile or self.default_profile()
        prompt = self.current_status(profile).prompt
        kind = classify_prompt(prompt) if prompt else None
        if remember and kind is not None:
            self.keyring.store(profile, kind, answer)
        self.backend_manager.answer_prompt(profile, answer)

    def forget_secrets(self, profile: VPNProfile | None = None) -> bool:
        """Remove every secret remembered for a profile.

        Returns False when the keyring is not reachable.
        """
        if not self.keyring.available:
            return False
        self.keyring.forget(profile or self.default_profile())
        return True

    def network_conflicts(self) -> list[DiagnosticItem]:
        """Conflicts between active VPNs, and between a VPN and the local network."""
        nm_backend = self.backend_manager.registry.get("networkmanager")
        snapshot = collect_snapshot(nm_backend.active_links())
        return find_conflicts(snapshot)

    def _keyring_answerer(self, profile: VPNProfile) -> Callable[[str], str | None]:
        def answer(prompt: str) -> str | None:
            kind = classify_prompt(prompt)
            return self.keyring.lookup(profile, kind) if kind is not None else None

        return answer

    def stop_unmanaged_connections(self) -> None:
        """Stop tunnels VPN Doctor runs itself, e.g. when the UI closes.

        NetworkManager connections are left alone: NetworkManager owns them
        and they normally outlive the window, like in GNOME Settings.
        """
        # Profiles of profiles.json share one openfortivpn process.
        unmanaged = next((p for p in self.profiles() if p.nm_uuid is None), None)
        if unmanaged is None:
            return
        if self.backend_manager.status(unmanaged).state != VPNConnectionState.DISCONNECTED:
            self.backend_manager.disconnect(unmanaged)

    def stop_connection(self, profile: VPNProfile | None = None) -> None:
        self.backend_manager.disconnect(profile or self.default_profile())

    def run(self, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="vpn-doctor")
        parser.add_argument("--version", action="store_true", help="Show VPN Doctor version")

        subparsers = parser.add_subparsers(dest="command")

        profile_option = argparse.ArgumentParser(add_help=False)
        profile_option.add_argument(
            "--profile",
            metavar="NAME",
            help="Profile or NetworkManager connection name (default: the first one)",
        )

        subparsers.add_parser("diagnose", help="Run basic diagnostics", parents=[profile_option])
        subparsers.add_parser("profiles", help="List VPN connections and profiles")
        subparsers.add_parser("status", help="Show connection status", parents=[profile_option])
        subparsers.add_parser("gui", help="Launch the experimental GTK UI")

        connect_parser = subparsers.add_parser(
            "connect",
            help="Connect a profile",
            parents=[profile_option],
        )
        connect_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the backend command without starting a VPN process",
        )
        connect_parser.add_argument(
            "--wait",
            action="store_true",
            help="Wait until the backend reports connected, failed or timeout",
        )
        connect_parser.add_argument(
            "--timeout",
            type=float,
            default=60.0,
            help="Maximum wait time in seconds when --wait is used",
        )

        subparsers.add_parser(
            "disconnect",
            help="Disconnect the active VPN session",
            parents=[profile_option],
        )

        subparsers.add_parser(
            "conflicts",
            help="Detect route and DNS conflicts between active VPNs and the local network",
        )

        subparsers.add_parser(
            "forget-secrets",
            help="Remove the secrets remembered in the keyring for a profile",
            parents=[profile_option],
        )

        rdp_parser = subparsers.add_parser(
            "rdp",
            help="Diagnose a Remote Desktop server reached through the VPN",
        )
        rdp_parser.add_argument("host", help="RDP server name or address")
        rdp_parser.add_argument("--port", type=int, default=DEFAULT_RDP_PORT)
        rdp_parser.add_argument(
            "--log",
            metavar="FILE",
            help="FreeRDP/Remmina log to explain, '-' for stdin "
            "(e.g. journalctl --user -b -o cat | vpn-doctor rdp HOST --log -)",
        )

        args = parser.parse_args(argv)

        if args.version:
            print("VPN Doctor 0.0.1")
            return 0

        if getattr(args, "profile", None):
            try:
                self.select_profile(args.profile)
            except ValueError as exc:
                print(exc)
                return 2

        if args.command == "diagnose":
            return self._diagnose()

        if args.command == "profiles":
            return self._profiles()

        if args.command == "status":
            return self._status()

        if args.command == "connect":
            return self._connect(
                dry_run=args.dry_run,
                wait=args.wait,
                timeout_seconds=args.timeout,
            )

        if args.command == "disconnect":
            return self._disconnect()

        if args.command == "conflicts":
            report = DiagnosticReport.from_items("Network conflicts", self.network_conflicts())
            if not report.items:
                print("No conflict between active VPNs and the local network.")
                return 0
            self._print_report(report)
            return 1

        if args.command == "forget-secrets":
            if not self.forget_secrets():
                print("The keyring is not reachable: install PyGObject and libsecret.")
                return 1
            print(f"Secrets forgotten for {self.default_profile().name}")
            return 0

        if args.command == "rdp":
            return self._rdp(args.host, args.port, args.log)

        if args.command == "gui":
            return self._gui()

        parser.print_help()
        return 0

    def _diagnose(self) -> int:
        profile = self.default_profile()
        result = self.backend_manager.diagnose(profile)
        self._print_report(result)
        return 0 if result.success else 1

    def _rdp(self, host: str, port: int, log_path: str | None) -> int:
        report = probe_rdp(host, port)
        self._print_report(report)
        success = report.success

        if log_path is not None:
            if log_path == "-":
                items = analyze_freerdp_log(sys.stdin)
            else:
                with Path(log_path).open(encoding="utf-8", errors="replace") as log_file:
                    items = analyze_freerdp_log(log_file)
            log_report = DiagnosticReport.from_items("RDP client log analysis", items)
            print()
            self._print_report(log_report)
            success = success and log_report.success

        return 0 if success else 1

    def _profiles(self) -> int:
        for profile in self.profiles():
            if profile.vpn_type:
                print(f"- {profile.name} ({profile.vpn_type} via NetworkManager)")
            else:
                print(f"- {profile.name} ({profile.backend})")
        return 0

    def _status(self) -> int:
        profile = self.default_profile()
        status = self.backend_manager.status(profile)
        self._print_status(status)
        return 0

    def _connect(self, dry_run: bool = False, wait: bool = False, timeout_seconds: float = 60.0) -> int:
        profile = self.default_profile()
        password = None
        if not dry_run and self.backend_manager.manages_secrets(profile) is False:
            password = self.secret_provider.get_password(profile) or self.stored_password()

        def print_log(line: str) -> None:
            print(line)

        try:
            result = self.backend_manager.connect(
                profile,
                password=password,
                on_log=print_log,
                dry_run=dry_run,
                wait=wait,
                timeout_seconds=timeout_seconds,
                prompt_handler=None if dry_run else self._keyring_answerer(profile),
            )
        except BackendProcessError as exc:
            print(f"Backend process error: {exc}")
            return 1

        if dry_run:
            print(" ".join(result))
            return 0

        if isinstance(result, VPNStatus):
            self._print_status(result)
            return 0 if result.state.value == "connected" else 1

        print("Connection started")
        return 0

    def _disconnect(self) -> int:
        profile = self.default_profile()
        self.backend_manager.disconnect(profile)
        print("Disconnected")
        return 0

    def _gui(self) -> int:
        from vpn_doctor.ui.main_window import run_ui

        return run_ui()

    @staticmethod
    def _print_report(report: DiagnosticReport) -> None:
        print(report.summary)
        for item in report.items:
            icon = "OK" if item.success else "FAIL"
            print(f"[{icon}] {item.name}: {item.message}")
            if item.suggestion:
                print(f"      Suggestion: {item.suggestion}")

    @staticmethod
    def _print_status(status: VPNStatus) -> None:
        print(f"{status.backend}: {status.state}")
        if status.message:
            print(status.message)
        if status.suggestion:
            print(f"Suggestion: {status.suggestion}")
