"""Application controller."""

from __future__ import annotations

import argparse

from vpn_doctor.backend.errors import BackendProcessError
from vpn_doctor.backend.manager import BackendManager
from vpn_doctor.backend.openfortivpn import OpenFortiVPNBackend
from vpn_doctor.backend.registry import BackendRegistry
from vpn_doctor.models.status import VPNStatus
from vpn_doctor.services.secret_service import EnvironmentSecretProvider
from vpn_doctor.services.settings_service import SettingsService


class ApplicationController:
    """High-level application coordinator."""

    def __init__(self) -> None:
        self.settings = SettingsService()
        self.secret_provider = EnvironmentSecretProvider()

        registry = BackendRegistry()
        registry.register(OpenFortiVPNBackend())
        self.backend_manager = BackendManager(registry=registry)

    def run(self, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="vpn-doctor")
        parser.add_argument("--version", action="store_true", help="Show VPN Doctor version")

        subparsers = parser.add_subparsers(dest="command")

        subparsers.add_parser("diagnose", help="Run basic diagnostics")
        subparsers.add_parser("profiles", help="List configured profiles")
        subparsers.add_parser("status", help="Show backend status")
        subparsers.add_parser("gui", help="Launch the experimental GTK UI")

        connect_parser = subparsers.add_parser("connect", help="Connect using the default profile")
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

        subparsers.add_parser("disconnect", help="Disconnect the active VPN session")

        args = parser.parse_args(argv)

        if args.version:
            print("VPN Doctor 0.0.1")
            return 0

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

        if args.command == "gui":
            return self._gui()

        parser.print_help()
        return 0

    def _diagnose(self) -> int:
        profile = self.settings.load_default_profile()
        result = self.backend_manager.diagnose(profile)

        print(result.summary)
        for item in result.items:
            icon = "OK" if item.success else "FAIL"
            print(f"[{icon}] {item.name}: {item.message}")
            if item.suggestion:
                print(f"      Suggestion: {item.suggestion}")

        return 0 if result.success else 1

    def _profiles(self) -> int:
        for profile in self.settings.load_profiles():
            print(f"- {profile.name} ({profile.backend})")
        return 0

    def _status(self) -> int:
        profile = self.settings.load_default_profile()
        status = self.backend_manager.status(profile)
        self._print_status(status)
        return 0

    def _connect(self, dry_run: bool = False, wait: bool = False, timeout_seconds: float = 60.0) -> int:
        profile = self.settings.load_default_profile()
        password = None if dry_run else self.secret_provider.get_password(profile)

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
        profile = self.settings.load_default_profile()
        self.backend_manager.disconnect(profile)
        print("Disconnected")
        return 0

    def _gui(self) -> int:
        from vpn_doctor.ui.main_window import run_ui

        return run_ui()

    @staticmethod
    def _print_status(status: VPNStatus) -> None:
        print(f"{status.backend}: {status.state}")
        if status.message:
            print(status.message)
