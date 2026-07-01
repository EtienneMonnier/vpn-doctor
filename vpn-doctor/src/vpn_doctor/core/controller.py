"""Application controller."""

from __future__ import annotations

import argparse
import getpass

from vpn_doctor import __version__
from vpn_doctor.backend.manager import BackendManager
from vpn_doctor.services.settings_service import SettingsService


class ApplicationController:
    """High-level application coordinator."""

    def __init__(self) -> None:
        self.settings = SettingsService()
        self.backends = BackendManager()

    def run(self, argv: list[str] | None = None) -> int:
        """Run the current CLI interface."""
        parser = argparse.ArgumentParser(prog="vpn-doctor")
        parser.add_argument("--version", action="store_true", help="Show VPN Doctor version")

        subparsers = parser.add_subparsers(dest="command")
        subparsers.add_parser("diagnose", help="Run basic diagnostics")
        subparsers.add_parser("profiles", help="List configured profiles")
        subparsers.add_parser("status", help="Show VPN status")

        connect_parser = subparsers.add_parser("connect", help="Connect to the default profile")
        connect_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate command construction without launching the VPN client",
        )
        connect_parser.add_argument(
            "--foreground",
            action="store_true",
            help="Run the VPN process in foreground and stream its lifecycle",
        )
        connect_parser.add_argument(
            "--ask-password",
            action="store_true",
            help="Ask for the VPN password and pass it to the backend process",
        )

        subparsers.add_parser("disconnect", help="Disconnect the active VPN session")

        args = parser.parse_args(argv)

        if args.version:
            print(f"VPN Doctor {__version__}")
            return 0

        if args.command == "diagnose":
            return self._diagnose()

        if args.command == "profiles":
            return self._profiles()

        if args.command == "status":
            return self._status()

        if args.command == "connect":
            password = getpass.getpass("VPN password: ") if args.ask_password else None
            return self._connect(
                password=password,
                dry_run=args.dry_run,
                foreground=args.foreground,
            )

        if args.command == "disconnect":
            return self._disconnect()

        parser.print_help()
        return 0

    def _diagnose(self) -> int:
        profile = self.settings.load_default_profile()
        result = self.backends.diagnose(profile)

        print(result.summary)
        for item in result.items:
            icon = "OK" if item.success else "FAIL"
            print(f"[{icon}] {item.name}: {item.message}")
            if item.suggestion:
                print(f"      Suggestion: {item.suggestion}")

        return 0 if result.success else 1

    def _profiles(self) -> int:
        profile = self.settings.load_default_profile()
        print(f"- {profile.name} ({profile.backend})")
        return 0

    def _status(self) -> int:
        profile = self.settings.load_default_profile()
        status = self.backends.status(profile)
        print(f"{status.backend}: {status.state}")
        if status.message:
            print(status.message)
        return 0

    def _connect(
        self,
        *,
        password: str | None,
        dry_run: bool,
        foreground: bool,
    ) -> int:
        profile = self.settings.load_default_profile()
        status = self.backends.connect(
            profile,
            password=password,
            dry_run=dry_run,
            foreground=foreground,
        )
        print(f"{status.backend}: {status.state}")
        if status.message:
            print(status.message)
        return 0 if status.state.value != "failed" else 1

    def _disconnect(self) -> int:
        profile = self.settings.load_default_profile()
        status = self.backends.disconnect(profile)
        print(f"{status.backend}: {status.state}")
        if status.message:
            print(status.message)
        return 0
