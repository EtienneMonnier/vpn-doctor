"""Secret providers.

VPN Doctor never writes secrets to files. Direct backends (openfortivpn) get
their secrets from:

1. the VPN_DOCTOR_PASSWORD environment variable (CLI experiments);
2. the desktop keyring through the freedesktop Secret Service API (libsecret).
   It works with GNOME Keyring today and with any other Secret Service
   provider, such as KeePassXC, without code changes.

NetworkManager connections do not use this module: NetworkManager asks the
GNOME secret agent itself.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from vpn_doctor.models.profile import VPNProfile

LOGGER = logging.getLogger(__name__)

SCHEMA_NAME = "io.github.vpndoctor.Secret"


class SecretKind(StrEnum):
    """Secrets VPN Doctor may remember. One-time codes are never stored."""

    PASSWORD = "password"
    PEM_PASSPHRASE = "pem-passphrase"


def classify_prompt(prompt: str) -> SecretKind | None:
    """Return which stored secret answers a backend prompt, if any."""
    lowered = prompt.lower()
    if any(word in lowered for word in ("one-time", "otp", "token", "two-factor", "code")):
        return None
    if "pem pass" in lowered or "private key" in lowered:
        return SecretKind.PEM_PASSPHRASE
    if "password" in lowered:
        return SecretKind.PASSWORD
    return None


class SecretProvider(Protocol):
    """Protocol implemented by secret providers."""

    def get_password(self, profile: VPNProfile) -> str | None:
        """Return a password for the profile or None."""


@dataclass(frozen=True)
class EnvironmentSecretProvider:
    """Read the VPN password from an environment variable (CLI experiments)."""

    variable_name: str = "VPN_DOCTOR_PASSWORD"

    def get_password(self, profile: VPNProfile) -> str | None:
        return os.environ.get(self.variable_name)


class KeyringSecretStore:
    """Store and read secrets in the desktop keyring through libsecret.

    Every method degrades to "nothing stored" when libsecret or the Secret
    Service is unavailable, so the CLI keeps working on minimal systems.
    """

    def __init__(self) -> None:
        self._secret = None
        self._schema = None
        self._error: type[Exception] = OSError

    def _load(self):
        if self._schema is not None:
            return self._secret, self._schema
        try:
            import gi  # type: ignore

            gi.require_version("Secret", "1")
            from gi.repository import GLib, Secret  # type: ignore
        except (ImportError, ValueError) as exc:
            LOGGER.info("libsecret is not available: %s", exc)
            return None, None

        self._secret = Secret
        self._error = GLib.Error
        self._schema = Secret.Schema.new(
            SCHEMA_NAME,
            Secret.SchemaFlags.NONE,
            {
                "profile": Secret.SchemaAttributeType.STRING,
                "kind": Secret.SchemaAttributeType.STRING,
            },
        )
        return self._secret, self._schema

    @staticmethod
    def _attributes(profile: VPNProfile, kind: SecretKind) -> dict[str, str]:
        return {"profile": profile.name, "kind": kind.value}

    @property
    def available(self) -> bool:
        return self._load()[1] is not None

    def lookup(self, profile: VPNProfile, kind: SecretKind) -> str | None:
        secret, schema = self._load()
        if schema is None:
            return None
        try:
            return secret.password_lookup_sync(schema, self._attributes(profile, kind), None)
        except self._error as exc:  # keyring locked, no Secret Service provider...
            LOGGER.warning("Cannot read the keyring: %s", exc)
            return None

    def store(self, profile: VPNProfile, kind: SecretKind, value: str) -> bool:
        secret, schema = self._load()
        if schema is None:
            return False
        label = f"VPN Doctor - {profile.name} ({kind.value})"
        try:
            return secret.password_store_sync(
                schema,
                self._attributes(profile, kind),
                secret.COLLECTION_DEFAULT,
                label,
                value,
                None,
            )
        except self._error as exc:
            LOGGER.warning("Cannot write to the keyring: %s", exc)
            return False

    def forget(self, profile: VPNProfile) -> None:
        secret, schema = self._load()
        if schema is None:
            return
        for kind in SecretKind:
            try:
                secret.password_clear_sync(schema, self._attributes(profile, kind), None)
            except self._error as exc:
                LOGGER.warning("Cannot clear the keyring: %s", exc)
