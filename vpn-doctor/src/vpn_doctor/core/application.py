"""Application bootstrap for VPN Doctor."""

from __future__ import annotations

from vpn_doctor.core.controller import ApplicationController
from vpn_doctor.services.logging_service import configure_logging


class VPNDoctorApplication:
    """Main application entry point."""

    def __init__(self) -> None:
        configure_logging()
        self.controller = ApplicationController()

    def run(self, argv: list[str] | None = None) -> int:
        """Run the command-line entry point for now."""
        return self.controller.run(argv)
