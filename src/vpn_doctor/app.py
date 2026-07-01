"""Console entry point for VPN Doctor."""

from __future__ import annotations

from vpn_doctor.core.application import VPNDoctorApplication


def main() -> int:
    """Run VPN Doctor."""
    app = VPNDoctorApplication()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
