"""Secret provider abstractions.

Sprint 2.3 deliberately avoids storing secrets. The first implementation reads
an optional password from the environment for CLI testing only.
"""

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

    This is useful for CLI experiments and tests. It is not meant to be the
    final UX. GNOME Keyring / Secret Service will be added later.
    """

    variable_name: str = "VPN_DOCTOR_PASSWORD"

    def get_password(self, profile: VPNProfile) -> str | None:
        return os.environ.get(self.variable_name)
