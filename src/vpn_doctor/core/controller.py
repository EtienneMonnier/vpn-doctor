"""Application controller."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

from vpn_doctor import __version__
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
from vpn_doctor.services.gateway_service import ApprovedGateway, GatewayService
from vpn_doctor.services.privilege_service import default_privilege_command, helper_command
from vpn_doctor.services.secret_service import (
    EnvironmentSecretProvider,
    KeyringSecretStore,
    SecretKind,
    classify_prompt,
)
from vpn_doctor.services.settings_service import SettingsService
from vpn_doctor.services.theme_service import Theme, ThemeService

JSON_HELP = "Print one JSON object instead of text (for scripts and agents)"


class ApplicationController:
    """High-level application coordinator."""

    def __init__(self) -> None:
        self.settings = SettingsService()
        self.theme_service = ThemeService()
        self.secret_provider = EnvironmentSecretProvider()
        self.keyring = KeyringSecretStore()
        self.gateways = GatewayService()

        registry = BackendRegistry()
        process = OpenFortiVPNProcess(
            privilege_command=default_privilege_command(),
            output_wrapper=line_buffering_command(),
            helper_command=helper_command(),
        )
        registry.register(OpenFortiVPNBackend(process=process))
        registry.register(NetworkManagerBackend())
        self.backend_manager = BackendManager(registry=registry)

        self.selected_profile_name: str | None = self.default_connection_name()
        self._profile_cache: list[VPNProfile] | None = None
        self._json_output = False

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

    def default_connection_name(self) -> str | None:
        """Connection opened at startup, chosen in Preferences."""
        return self.settings.load_settings().get("default_connection")

    def set_default_connection(self, name: str | None) -> None:
        self.settings.save_setting("default_connection", name)

    def autoconnect_enabled(self) -> bool:
        return bool(self.settings.load_settings().get("autoconnect", False))

    def set_autoconnect(self, enabled: bool) -> None:
        self.settings.save_setting("autoconnect", enabled)

    def startup_connection(self) -> VPNProfile | None:
        """The default connection to connect at startup, if auto-connect is on."""
        name = self.default_connection_name()
        if not self.autoconnect_enabled() or name is None:
            return None
        return next((p for p in self.profiles() if p.name == name), None)

    def connection_editor_command(self, profile: VPNProfile | None = None) -> list[str] | None:
        """Command opening the NetworkManager editor, to create or edit a connection."""
        if shutil.which("nm-connection-editor"):
            if profile is not None and profile.nm_uuid:
                return ["nm-connection-editor", f"--edit={profile.nm_uuid}"]
            return ["nm-connection-editor", "--create", "--type=vpn"]
        if shutil.which("gnome-control-center"):
            return ["gnome-control-center", "network"]
        return None

    def boot_animation_enabled(self) -> bool:
        return bool(self.settings.load_settings().get("boot_animation", True))

    def set_boot_animation(self, enabled: bool) -> None:
        self.settings.save_setting("boot_animation", enabled)

    def boot_report(self) -> dict:
        """Facts shown by the startup animation."""
        nm_backend = self.backend_manager.registry.get("networkmanager")
        return {
            "connections": len(self.profiles()),
            "networkmanager": nm_backend.is_available(),
            "keyring": self.keyring.available,
        }

    def direct_profiles(self) -> list[VPNProfile]:
        """Profiles VPN Doctor runs itself, whose secrets it may remember."""
        return [profile for profile in self.profiles() if profile.nm_uuid is None]

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

    def needs_gateway_approval(self, profile: VPNProfile | None = None) -> bool:
        """True when the helper will refuse this gateway until it is approved."""
        return self.gateways.needs_approval(profile or self.default_profile())

    def approve_gateway(self, profile: VPNProfile | None = None) -> tuple[bool, str]:
        """Approve the profile's gateway; asks for an administrator password."""
        return self.gateways.approve(profile or self.default_profile())

    def approved_gateways(self) -> list[ApprovedGateway]:
        return self.gateways.approved()

    def revoke_gateway(self, gateway: ApprovedGateway) -> tuple[bool, str]:
        return self.gateways.revoke(gateway)

    def network_conflicts(self) -> list[DiagnosticItem]:
        """Conflicts between active VPNs, and between a VPN and the local network."""
        nm_backend = self.backend_manager.registry.get("networkmanager")
        snapshot = collect_snapshot(nm_backend.active_links())

        # openfortivpn runs pppd: name its ppp interface after the profile.
        unmanaged = next((p for p in self.profiles() if p.nm_uuid is None), None)
        if unmanaged is not None and self.backend_manager.status(unmanaged).state in {
            VPNConnectionState.CONNECTED,
            VPNConnectionState.CONNECTING,
        }:
            for link in snapshot.vpn_links:
                if link.startswith("ppp"):
                    snapshot.vpn_links[link] = unmanaged.name
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
        parser.add_argument("--json", action="store_true", help=JSON_HELP)

        subparsers = parser.add_subparsers(dest="command")

        # Also accepted after the command; SUPPRESS keeps the global value.
        json_option = argparse.ArgumentParser(add_help=False)
        json_option.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=JSON_HELP)

        profile_option = argparse.ArgumentParser(add_help=False, parents=[json_option])
        profile_option.add_argument(
            "--profile",
            metavar="NAME",
            help="Profile or NetworkManager connection name (default: the first one)",
        )

        subparsers.add_parser("diagnose", help="Run basic diagnostics", parents=[profile_option])
        subparsers.add_parser("profiles", help="List VPN connections and profiles", parents=[json_option])
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
            "gateways",
            help="List the gateways approved on this computer",
            parents=[json_option],
        )
        subparsers.add_parser(
            "approve-gateway",
            help="Approve the gateway of a profile (administrator password)",
            parents=[profile_option],
        )
        revoke_parser = subparsers.add_parser(
            "revoke-gateway",
            help="Revoke an approved gateway (administrator password)",
            parents=[json_option],
        )
        revoke_parser.add_argument("gateway", metavar="HOST:PORT")

        subparsers.add_parser(
            "conflicts",
            help="Detect route and DNS conflicts between active VPNs and the local network",
            parents=[json_option],
        )

        subparsers.add_parser(
            "forget-secrets",
            help="Remove the secrets remembered in the keyring for a profile",
            parents=[profile_option],
        )

        rdp_parser = subparsers.add_parser(
            "rdp",
            help="Diagnose a Remote Desktop server reached through the VPN",
            parents=[json_option],
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
        self._json_output = args.json

        if args.version:
            return self._output({"version": __version__}, f"VPN Doctor {__version__}")

        if getattr(args, "profile", None):
            try:
                self.select_profile(args.profile)
            except ValueError as exc:
                return self._error(str(exc), 2)

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

        if args.command == "gateways":
            return self._gateways()

        if args.command == "approve-gateway":
            ok, message = self.approve_gateway()
            return self._result(ok, message)

        if args.command == "revoke-gateway":
            host, _, port = args.gateway.rpartition(":")
            if not port.isdigit():
                return self._error("Expected HOST:PORT", 2)
            ok, message = self.revoke_gateway(ApprovedGateway(host.lower(), int(port)))
            return self._result(ok, message)

        if args.command == "conflicts":
            return self._conflicts()

        if args.command == "forget-secrets":
            if not self.forget_secrets():
                return self._error("The keyring is not reachable: install PyGObject and libsecret.", 1)
            name = self.default_profile().name
            return self._result(True, f"Secrets forgotten for {name}", profile=name)

        if args.command == "rdp":
            return self._rdp(args.host, args.port, args.log)

        if args.command == "gui":
            return self._gui()

        parser.print_help()
        return 0

    def _diagnose(self) -> int:
        profile = self.default_profile()
        result = self.backend_manager.diagnose(profile)
        if self._json_output:
            self._emit({"profile": profile.name, "report": result.to_dict()})
        else:
            self._print_report(result)
        return 0 if result.success else 1

    def _conflicts(self) -> int:
        report = DiagnosticReport.from_items("Network conflicts", self.network_conflicts())
        if self._json_output:
            self._emit({"report": report.to_dict()})
        elif not report.items:
            print("No conflict between active VPNs and the local network.")
        else:
            self._print_report(report)
        return 0 if report.success else 1

    def _rdp(self, host: str, port: int, log_path: str | None) -> int:
        report = probe_rdp(host, port)
        log_report = None
        if log_path is not None:
            try:
                if log_path == "-":
                    items = analyze_freerdp_log(sys.stdin)
                else:
                    with Path(log_path).open(encoding="utf-8", errors="replace") as log_file:
                        items = analyze_freerdp_log(log_file)
            except OSError as exc:
                return self._error(f"Cannot read {log_path}: {exc.strerror}", 2)
            log_report = DiagnosticReport.from_items("RDP client log analysis", items)

        if self._json_output:
            self._emit(
                {
                    "host": host,
                    "port": port,
                    "probe": report.to_dict(),
                    "log_analysis": log_report.to_dict() if log_report else None,
                }
            )
        else:
            self._print_report(report)
            if log_report is not None:
                print()
                self._print_report(log_report)

        success = report.success and (log_report is None or log_report.success)
        return 0 if success else 1

    def _profiles(self) -> int:
        profiles = self.profiles()
        if self._json_output:
            self._emit({"profiles": [profile.to_dict() for profile in profiles]})
            return 0
        for profile in profiles:
            if profile.vpn_type:
                print(f"- {profile.name} ({profile.vpn_type} via NetworkManager)")
            else:
                print(f"- {profile.name} ({profile.backend})")
        return 0

    def _status(self) -> int:
        profile = self.default_profile()
        status = self.backend_manager.status(profile)
        if self._json_output:
            self._emit({"profile": profile.name, "status": status.to_dict()})
        else:
            self._print_status(status)
        return 0

    def _gateways(self) -> int:
        gateways = self.approved_gateways()
        if self._json_output:
            self._emit(
                {
                    "enforced": self.gateways.enforced,
                    "gateways": [
                        {"host": g.host, "port": g.port, "trusted_cert": g.trusted_cert} for g in gateways
                    ],
                }
            )
            return 0
        if not self.gateways.enforced:
            print("The privileged helper is not installed: gateways need no approval.")
        for gateway in gateways:
            pin = gateway.trusted_cert[:16] + "…" if gateway.trusted_cert else "system CA"
            print(f"- {gateway.label} (certificate: {pin})")
        return 0

    def _connect(self, dry_run: bool = False, wait: bool = False, timeout_seconds: float = 60.0) -> int:
        profile = self.default_profile()
        password = None
        if not dry_run and self.backend_manager.manages_secrets(profile) is False:
            password = self.secret_provider.get_password(profile) or self.stored_password()

        # In JSON mode the backend logs go into the result, not before it.
        logs: list[str] = []
        on_log = logs.append if self._json_output else print

        try:
            result = self.backend_manager.connect(
                profile,
                password=password,
                on_log=on_log,
                dry_run=dry_run,
                wait=wait,
                timeout_seconds=timeout_seconds,
                prompt_handler=None if dry_run else self._keyring_answerer(profile),
            )
        except BackendProcessError as exc:
            return self._error(f"Backend process error: {exc}", 1, logs=logs)

        if dry_run:
            return self._output({"profile": profile.name, "command": list(result)}, " ".join(result))

        if isinstance(result, VPNStatus):
            code = 0 if result.state == VPNConnectionState.CONNECTED else 1
            if self._json_output:
                self._emit({"profile": profile.name, "status": result.to_dict(), "logs": logs})
            else:
                self._print_status(result)
            return code

        return self._output({"profile": profile.name, "started": True, "logs": logs}, "Connection started")

    def _disconnect(self) -> int:
        profile = self.default_profile()
        self.backend_manager.disconnect(profile)
        return self._output({"profile": profile.name, "disconnected": True}, "Disconnected")

    def _gui(self) -> int:
        from vpn_doctor.ui.main_window import run_ui

        return run_ui()

    # Output helpers: text for people, one JSON object on stdout with --json.

    def _output(self, data: dict, text: str, code: int = 0) -> int:
        if self._json_output:
            self._emit(data)
        else:
            print(text)
        return code

    def _result(self, ok: bool, message: str, **extra: object) -> int:
        return self._output({"success": ok, "message": message, **extra}, message, 0 if ok else 1)

    def _error(self, message: str, code: int, **extra: object) -> int:
        return self._output({"error": message, **extra}, message, code)

    @staticmethod
    def _emit(data: dict) -> None:
        print(json.dumps(data, indent=2, ensure_ascii=False))

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
