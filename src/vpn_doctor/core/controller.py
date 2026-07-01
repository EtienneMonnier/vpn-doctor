"""Application controller."""

from __future__ import annotations

import argparse

from vpn_doctor.backend.manager import BackendManager
from vpn_doctor.backend.openfortivpn import OpenFortiVPNBackend
from vpn_doctor.backend.registry import BackendRegistry
from vpn_doctor.services.settings_service import SettingsService


class ApplicationController:
    """High-level application coordinator."""

    def __init__(self) -> None:
        self.settings = SettingsService()

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

        connect_parser = subparsers.add_parser("connect", help="Connect using the default profile")
        connect_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the backend command without starting a VPN process",
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
            return self._connect(dry_run=args.dry_run)

        if args.command == "disconnect":
            return self._disconnect()

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
        profile = self.settings.load_default_profile()
        print(f"- {profile.name} ({profile.backend})")
        return 0

    def _status(self) -> int:
        profile = self.settings.load_default_profile()
        status = self.backend_manager.status(profile)
        print(f"{status.backend}: {status.state}")
        if status.message:
            print(status.message)
        return 0

    def _connect(self, dry_run: bool = False) -> int:
        profile = self.settings.load_default_profile()
        command = self.backend_manager.connect(profile, dry_run=dry_run)

        if dry_run:
            print(" ".join(command))
            return 0

        print("Connection started")
        return 0

    def _disconnect(self) -> int:
        profile = self.settings.load_default_profile()
        self.backend_manager.disconnect(profile)
        print("Disconnected")
        return 0
