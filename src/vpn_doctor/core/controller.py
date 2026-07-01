"""Application controller."""

from __future__ import annotations

import argparse

from vpn_doctor import __version__
from vpn_doctor.backend.openfortivpn import OpenFortiVPNBackend
from vpn_doctor.services.settings_service import SettingsService


class ApplicationController:
    """High-level application coordinator."""

    def __init__(self) -> None:
        self.settings = SettingsService()
        self.backend = OpenFortiVPNBackend()

    def run(self, argv: list[str] | None = None) -> int:
        """Run the current CLI interface."""
        parser = argparse.ArgumentParser(prog="vpn-doctor")
        parser.add_argument("--version", action="store_true", help="Show VPN Doctor version")

        subparsers = parser.add_subparsers(dest="command")
        subparsers.add_parser("diagnose", help="Run basic diagnostics")
        subparsers.add_parser("profiles", help="List configured profiles")

        args = parser.parse_args(argv)

        if args.version:
            print(f"VPN Doctor {__version__}")
            return 0

        if args.command == "diagnose":
            return self._diagnose()

        if args.command == "profiles":
            return self._profiles()

        parser.print_help()
        return 0

    def _diagnose(self) -> int:
        profile = self.settings.load_default_profile()
        result = self.backend.diagnose(profile)

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
