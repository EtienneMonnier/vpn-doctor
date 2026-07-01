"""Secret provider abstractions."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from vpn_doctor.models.profile import VPNProfile


class SecretProvider(Protocol):
    """Protocol implemented by secret providers."""

    def get_password(self, profile: VPNProfile) -> str | None:
        """Return a password for the profile or None."""


@dataclass(frozen=True)
class EnvironmentSecretProvider:
    """Read VPN passwords from environment variables.

    This is a temporary CLI-oriented provider. GNOME Keyring integration will
    replace it for the desktop UX.
    """

    variable_name: str = "VPN_DOCTOR_PASSWORD"

    def get_password(self, profile: VPNProfile) -> str | None:
        return os.environ.get(self.variable_name)
