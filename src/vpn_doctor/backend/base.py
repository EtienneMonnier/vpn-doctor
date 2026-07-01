"""Common VPN backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.models.status import ConnectionStatus


class VPNBackend(ABC):
    """Base class for all VPN backends."""

    @abstractmethod
    def connect(self, profile: VPNProfile) -> None:
        """Start a VPN connection."""

    @abstractmethod
    def disconnect(self) -> None:
        """Stop the VPN connection."""

    @abstractmethod
    def status(self) -> ConnectionStatus:
        """Return current connection status."""
