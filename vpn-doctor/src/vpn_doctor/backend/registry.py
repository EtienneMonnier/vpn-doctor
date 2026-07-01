"""VPN backend registry."""

from __future__ import annotations

from dataclasses import dataclass, field

from vpn_doctor.backend.base import VPNBackend


@dataclass
class BackendRegistry:
    """Registry of available VPN backends."""

    _backends: dict[str, VPNBackend] = field(default_factory=dict)

    def register(self, backend: VPNBackend) -> None:
        self._backends[backend.name] = backend

    def get(self, name: str) -> VPNBackend:
        try:
            return self._backends[name]
        except KeyError as exc:
            available = ", ".join(sorted(self._backends)) or "none"
            raise KeyError(f"Unknown VPN backend '{name}'. Available backends: {available}") from exc

    def names(self) -> list[str]:
        return sorted(self._backends)
