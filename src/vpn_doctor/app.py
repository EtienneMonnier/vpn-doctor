from vpn_doctor.core.application import VPNDoctorApplication


def main() -> int:
    app = VPNDoctorApplication()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
