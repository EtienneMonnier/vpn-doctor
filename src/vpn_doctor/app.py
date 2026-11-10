"""VPN Doctor application entry point."""

from __future__ import annotations

from vpn_doctor.core.application import VPNDoctorApplication


def main(argv: list[str] | None = None) -> int:
    app = VPNDoctorApplication()
    return app.run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
