"""Backend registry."""

from __future__ import annotations

from dataclasses import dataclass, field

from vpn_doctor.backend.base import VPNBackend
from vpn_doctor.backend.errors import BackendNotFoundError


@dataclass
class BackendRegistry:
    """Store available backend instances."""

    _backends: dict[str, VPNBackend] = field(default_factory=dict)

    def register(self, backend: VPNBackend) -> None:
        self._backends[backend.name] = backend

    def get(self, name: str) -> VPNBackend:
        try:
            return self._backends[name]
        except KeyError as exc:
            raise BackendNotFoundError(f"Backend not registered: {name}") from exc

    def names(self) -> list[str]:
        return sorted(self._backends)
