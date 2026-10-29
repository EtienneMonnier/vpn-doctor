"""Gateways approved for the privileged helper (ADR-0013).

The list is readable by everyone; changing it goes through the helper and an
administrator password. The rules here mirror the helper's check, so the UI
can ask for approval before connecting; the helper still decides.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.services.privilege_service import HELPER_PATH, helper_command

LOGGER = logging.getLogger(__name__)

APPROVED_GATEWAYS = Path("/etc/vpn-doctor/gateways.json")


@dataclass(frozen=True)
class ApprovedGateway:
    host: str
    port: int
    trusted_cert: str | None = None

    @property
    def label(self) -> str:
        return f"{self.host}:{self.port}"


class GatewayService:
    def __init__(self, path: Path = APPROVED_GATEWAYS, helper: Path = HELPER_PATH) -> None:
        self.path = path
        self.helper = helper

    @property
    def enforced(self) -> bool:
        """Approval only exists with the installed helper."""
        return bool(helper_command(self.helper))

    def approved(self) -> list[ApprovedGateway]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except (OSError, ValueError) as exc:
            LOGGER.warning("Cannot read %s: %s", self.path, exc)
            return []
        gateways = []
        for raw in data.get("gateways", []) if isinstance(data, dict) else []:
            if isinstance(raw, dict) and isinstance(raw.get("port"), int):
                gateways.append(
                    ApprovedGateway(str(raw.get("host", "")).lower(), raw["port"], raw.get("trusted_cert"))
                )
        return gateways

    def is_approved(self, profile: VPNProfile) -> bool:
        fingerprint = profile.trusted_cert.lower() if profile.trusted_cert else None
        return ApprovedGateway(profile.host.lower(), profile.port, fingerprint) in self.approved()

    def needs_approval(self, profile: VPNProfile) -> bool:
        return profile.nm_uuid is None and self.enforced and not self.is_approved(profile)

    def approve(self, profile: VPNProfile) -> tuple[bool, str]:
        request = {"host": profile.host, "port": profile.port}
        if profile.trusted_cert:
            request["trusted_cert"] = profile.trusted_cert
        return self._run("approve", request)

    def revoke(self, gateway: ApprovedGateway) -> tuple[bool, str]:
        return self._run("revoke", {"host": gateway.host, "port": gateway.port})

    def _run(self, action: str, request: dict) -> tuple[bool, str]:
        command = helper_command(self.helper, action)
        if not command:
            return False, "The VPN Doctor helper is not installed"
        try:
            result = subprocess.run(
                command,
                check=False,
                input=json.dumps(request) + "\n",
                capture_output=True,
                text=True,
                timeout=300,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return False, str(exc)
        output = (result.stdout + result.stderr).strip()
        return result.returncode == 0, output
