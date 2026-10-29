"""NetworkManager backend.

VPN Doctor does not replace NetworkManager: connections are still created in
GNOME Settings or nm-connection-editor, passwords are still asked by the GNOME
secret agent and stored in the keyring, and NetworkManager handles privileges.

This backend drives existing connections through `nmcli`, follows the
NetworkManager journal while a connection is active, and explains failures.
See docs/adr/0011-networkmanager-overlay.md.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from vpn_doctor.backend.base import VPNBackend
from vpn_doctor.backend.errors import BackendProcessError
from vpn_doctor.backend.process_runner import ProcessRunner
from vpn_doctor.backend.state_machine import ConnectionStateMachine
from vpn_doctor.diagnostics.vpn_plugins import explain_failure
from vpn_doctor.models.diagnostic import DiagnosticItem, DiagnosticReport
from vpn_doctor.models.profile import VPNProfile
from vpn_doctor.models.status import VPNConnectionState, VPNStatus

LOGGER = logging.getLogger(__name__)

VPN_SERVICE_PREFIX = "org.freedesktop.NetworkManager."
VPN_PLUGIN_DIRS = (Path("/usr/lib/NetworkManager/VPN"), Path("/etc/NetworkManager/VPN"))

ACTIVE_STATES = {
    "activating": VPNConnectionState.CONNECTING,
    "activated": VPNConnectionState.CONNECTED,
    "deactivating": VPNConnectionState.DISCONNECTING,
}

# Keys of `vpn.data` holding the gateway, per plugin.
GATEWAY_KEYS = ("gateway", "remote")


def split_terse(line: str) -> list[str]:
    """Split one line of `nmcli -t` output, honouring backslash escapes."""
    fields: list[str] = []
    current: list[str] = []
    escaped = False
    for char in line:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(char)
    fields.append("".join(current))
    return fields


def unescape_value(value: str) -> str:
    """Undo the escaping of `nmcli -g`, which writes ':' as '\\:'."""
    return value.replace("\\:", ":").replace("\\\\", "\\")


def parse_vpn_data(data: str) -> dict[str, str]:
    """Parse `vpn.data` ("key = value, key = value") into a dict."""
    result: dict[str, str] = {}
    for part in unescape_value(data).split(","):
        key, separator, value = part.partition("=")
        if separator:
            result[key.strip()] = value.strip()
    return result


def parse_gateway(value: str) -> tuple[str, int]:
    """Extract host and port from a plugin gateway value.

    Accepts "host", "host:port", "host port", "host:port:udp" (openvpn) and
    URLs such as "https://host:8443/group" (openconnect).
    """
    value = value.split(",")[0].strip()
    if "://" in value:
        url = urlsplit(value)
        return url.hostname or "", url.port or 0
    host, _, rest = value.replace(" ", ":").partition(":")
    port = rest.split(":")[0]
    return host, int(port) if port.isdigit() else 0


def parse_addresses(output: str) -> set[str]:
    """Return the addresses, without prefix, of `nmcli -g IP4.ADDRESS,IP6.ADDRESS`."""
    addresses = set()
    for line in unescape_value(output).splitlines():
        for value in line.split("|"):
            address = value.strip().split("/")[0]
            if address:
                addresses.add(address)
    return addresses


def interface_for_addresses(addresses: set[str], ip_addr_json: str) -> str | None:
    """Return the interface that carries one of the addresses (`ip -j addr`)."""
    try:
        interfaces = json.loads(ip_addr_json or "[]")
    except ValueError:
        return None
    for interface in interfaces:
        for info in interface.get("addr_info", []):
            if info.get("local") in addresses:
                return interface.get("ifname")
    return None


def parse_journal_entry(raw: str) -> tuple[str, str] | None:
    """Return (syslog identifier, message) of one `journalctl -o json` line."""
    try:
        entry = json.loads(raw)
    except ValueError:
        return None
    message = entry.get("MESSAGE")
    if not isinstance(message, str) or not message.strip():
        return None
    return entry.get("SYSLOG_IDENTIFIER") or "", message


def belongs_to(entry: tuple[str, str], profile: VPNProfile) -> bool:
    """Tell whether a NetworkManager journal entry concerns this connection.

    NetworkManager logs every device: keep its lines that name the connection.
    VPN plugins log under their own identifier, e.g. "nm-openvpn".
    """
    identifier, message = entry
    if identifier == "NetworkManager":
        return bool(profile.nm_uuid and profile.nm_uuid in message) or profile.name in message
    if profile.vpn_type and profile.vpn_type in identifier:
        return True
    # Helpers such as pppd cannot be attributed: show them to every session.
    return not identifier.startswith("nm-")


@dataclass
class Session:
    """One connection started by VPN Doctor: its nmcli call, journal and state."""

    profile: VPNProfile
    runner: ProcessRunner = field(default_factory=ProcessRunner)
    journal: ProcessRunner = field(default_factory=ProcessRunner)
    state_machine: ConnectionStateMachine = field(default_factory=ConnectionStateMachine)
    activation_lines: list[str] = field(default_factory=list)
    plugin_lines: list[str] = field(default_factory=list)

    def stop_processes(self) -> None:
        self.runner.terminate()
        self.journal.terminate()


@dataclass
class NetworkManagerBackend(VPNBackend):
    """Drive NetworkManager VPN and WireGuard connections, several at once."""

    name: str = "networkmanager"
    manages_secrets: bool = True
    activation_timeout: int = 120
    sessions: dict[str, Session] = field(default_factory=dict)

    # -- discovery ---------------------------------------------------------

    def list_profiles(self) -> list[VPNProfile]:
        if not shutil.which("nmcli"):
            return []

        try:
            output = self._nmcli("-t", "-f", "NAME,UUID,TYPE", "connection", "show")
        except BackendProcessError as exc:
            LOGGER.warning("Cannot list NetworkManager connections: %s", exc)
            return []

        profiles = []
        for line in output.splitlines():
            name, uuid, kind = split_terse(line)[:3]
            if kind == "wireguard":
                profiles.append(self._profile_for(name, uuid, "wireguard", {}))
            elif kind == "vpn":
                service = self._nmcli("-g", "vpn.service-type", "connection", "show", "uuid", uuid)
                data = parse_vpn_data(self._nmcli("-g", "vpn.data", "connection", "show", "uuid", uuid))
                vpn_type = service.strip().removeprefix(VPN_SERVICE_PREFIX)
                profiles.append(self._profile_for(name, uuid, vpn_type, data))
        return profiles

    def _profile_for(self, name: str, uuid: str, vpn_type: str, data: dict[str, str]) -> VPNProfile:
        host, port = "", 0
        for key in GATEWAY_KEYS:
            if data.get(key):
                host, port = parse_gateway(data[key])
                break
        return VPNProfile(
            name=name,
            backend=self.name,
            host=host,
            port=port,
            nm_uuid=uuid,
            vpn_type=vpn_type,
        )

    # -- lifecycle -------------------------------------------------------------

    def connect(
        self,
        profile: VPNProfile,
        password: str | None = None,
        on_log: Callable[[str], None] | None = None,
        dry_run: bool = False,
        wait: bool = False,
        timeout_seconds: float = 120.0,
        prompt_handler: Callable[[str], str | None] | None = None,
    ) -> list[str] | VPNStatus:
        """Activate the NetworkManager connection.

        The password and prompt_handler arguments are ignored: NetworkManager
        asks for secrets through the GNOME secret agent and its keyring.
        """
        command = [
            "nmcli",
            "--wait",
            str(self.activation_timeout),
            "connection",
            "up",
            "uuid",
            profile.nm_uuid or "",
        ]
        if dry_run:
            return command

        previous = self.sessions.get(profile.nm_uuid or "")
        if previous is not None:
            previous.stop_processes()
        session = Session(profile=profile)
        self.sessions[profile.nm_uuid or ""] = session
        session.state_machine.transition(VPNConnectionState.CONNECTING, "Asking NetworkManager")

        self._follow_journal(session, on_log)
        session.runner.start(
            command,
            on_line=lambda line: self._handle_activation_line(session, line, on_log),
            stdin_text="",
        )

        if wait:
            return self._wait(session, timeout_seconds)
        return command

    def disconnect(self, profile: VPNProfile | None = None) -> None:
        """Disconnect one connection, or every connection VPN Doctor started."""
        targets = [profile] if profile is not None else [s.profile for s in self.sessions.values()]
        for target in targets:
            session = self.sessions.get(target.nm_uuid or "")
            if session is not None:
                session.state_machine.transition(
                    VPNConnectionState.DISCONNECTING, "Asking NetworkManager"
                )
                session.runner.terminate()
            if target.nm_uuid:
                subprocess.run(
                    ["nmcli", "connection", "down", "uuid", target.nm_uuid],
                    check=False,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            if session is not None:
                session.journal.terminate()
                session.state_machine.transition(VPNConnectionState.DISCONNECTED, "Disconnected")

    def status(self, profile: VPNProfile | None = None) -> VPNStatus:
        if profile is None:
            if not self.sessions:
                return VPNStatus(backend=self.name, state=VPNConnectionState.DISCONNECTED)
            profile = list(self.sessions.values())[-1].profile

        session = self.sessions.get(profile.nm_uuid or "")
        if session is None:
            # A connection VPN Doctor did not start: NetworkManager is the only source.
            state = self._active_state(profile.nm_uuid or "") or VPNConnectionState.DISCONNECTED
            return VPNStatus(backend=self.name, state=state)

        machine = session.state_machine
        # While nmcli is still activating, its output is the freshest source.
        if not session.runner.is_running:
            nm_state = self._active_state(profile.nm_uuid or "")
            if nm_state is not None:
                if machine.state != nm_state:
                    machine.transition(nm_state, None)
            elif machine.state != VPNConnectionState.FAILED:
                machine.state = VPNConnectionState.DISCONNECTED

        return VPNStatus(
            backend=self.name,
            state=machine.state,
            message=machine.last_message,
            suggestion=machine.suggestion,
        )

    def active_links(self) -> dict[str, str]:
        """Return {network interface: connection name} for active VPN connections."""
        try:
            output = self._nmcli("-t", "-f", "NAME,UUID,TYPE,DEVICE", "connection", "show", "--active")
        except BackendProcessError:
            return {}
        links = {}
        for line in output.splitlines():
            name, uuid, kind, device = (split_terse(line) + ["", "", "", ""])[:4]
            if kind == "wireguard" and device:
                links[device] = name
            elif kind == "vpn":
                # nmcli reports the underlying device (e.g. Wi-Fi) as the IP
                # interface of plugin VPNs; find the tunnel by its address.
                output = self._nmcli("-g", "IP4.ADDRESS,IP6.ADDRESS", "connection", "show", "uuid", uuid)
                iface = interface_for_addresses(parse_addresses(output), self._ip_addresses())
                if iface:
                    links[iface] = name
        return links

    @staticmethod
    def _ip_addresses() -> str:
        try:
            return subprocess.run(
                ["ip", "-j", "addr", "show"],
                check=True,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=5,
            ).stdout
        except (OSError, subprocess.SubprocessError) as exc:
            LOGGER.warning("Cannot list network addresses: %s", exc)
            return "[]"

    def diagnose(self, profile: VPNProfile) -> DiagnosticReport:
        items = [self._check_nmcli()]
        if profile.vpn_type and profile.vpn_type != "wireguard":
            items.append(self._check_plugin(profile.vpn_type))
        return DiagnosticReport.from_items("NetworkManager diagnostics", items)

    # -- activation output and journal -------------------------------------------

    def _handle_activation_line(
        self,
        session: Session,
        line: str,
        on_log: Callable[[str], None] | None,
    ) -> None:
        if not line.strip():
            return
        session.activation_lines.append(line)
        if on_log is not None:
            on_log(line)

        if "successfully activated" in line:
            session.state_machine.transition(VPNConnectionState.CONNECTED, line)
        elif line.startswith("Error:"):
            self._fail(session, line)

    @staticmethod
    def _fail(session: Session, message: str) -> None:
        # Give the journal follower a moment to receive the plugin's last words.
        time.sleep(0.5)
        explanations = explain_failure(session.activation_lines, session.plugin_lines)
        session.state_machine.transition(VPNConnectionState.FAILED, message)
        if explanations:
            first = explanations[0]
            session.state_machine.suggestion = f"{first.message} {first.suggestion or ''}".strip()
        session.journal.terminate()

    def _follow_journal(self, session: Session, on_log: Callable[[str], None] | None) -> None:
        if not shutil.which("journalctl"):
            return

        def handle(raw: str) -> None:
            entry = parse_journal_entry(raw)
            if entry is None or not belongs_to(entry, session.profile):
                return
            identifier, message = entry
            if identifier != "NetworkManager":
                session.plugin_lines.append(message)
            if on_log is not None:
                on_log(message)

        try:
            session.journal.start(
                ["journalctl", "--follow", "--lines=0", "--output=json", "--unit=NetworkManager"],
                on_line=handle,
            )
        except BackendProcessError as exc:
            LOGGER.warning("Cannot follow the NetworkManager journal: %s", exc)

    def _wait(self, session: Session, timeout_seconds: float) -> VPNStatus:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            status = self.status(session.profile)
            if status.state in {VPNConnectionState.CONNECTED, VPNConnectionState.FAILED}:
                return status
            if not session.runner.is_running and status.state == VPNConnectionState.DISCONNECTED:
                return status
            time.sleep(0.2)
        session.state_machine.transition(VPNConnectionState.FAILED, "Connection timeout")
        return self.status(session.profile)

    # -- helpers -----------------------------------------------------------------

    def _active_state(self, uuid: str) -> VPNConnectionState | None:
        try:
            output = self._nmcli("-t", "-f", "UUID,STATE", "connection", "show", "--active")
        except BackendProcessError:
            return None
        for line in output.splitlines():
            fields = split_terse(line)
            if len(fields) >= 2 and fields[0] == uuid:
                return ACTIVE_STATES.get(fields[1])
        return None

    @staticmethod
    def _nmcli(*args: str) -> str:
        try:
            result = subprocess.run(
                ["nmcli", *args],
                check=True,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise BackendProcessError(str(exc)) from exc
        return result.stdout

    def _check_nmcli(self) -> DiagnosticItem:
        try:
            running = self._nmcli("-t", "-f", "RUNNING", "general").strip()
        except BackendProcessError:
            running = ""
        if running == "running":
            return DiagnosticItem("NetworkManager", True, "NetworkManager is running")
        return DiagnosticItem(
            "NetworkManager",
            False,
            "NetworkManager is not reachable through nmcli",
            "Check that NetworkManager is installed and running: systemctl status NetworkManager",
        )

    @staticmethod
    def _check_plugin(vpn_type: str) -> DiagnosticItem:
        service = f"service={VPN_SERVICE_PREFIX}{vpn_type}"
        for directory in VPN_PLUGIN_DIRS:
            if not directory.is_dir():
                continue
            for name_file in directory.glob("*.name"):
                if service in name_file.read_text(encoding="utf-8", errors="replace"):
                    return DiagnosticItem("VPN plugin", True, f"The {vpn_type} plugin is installed")
        return DiagnosticItem(
            "VPN plugin",
            False,
            f"The NetworkManager {vpn_type} plugin is missing",
            f"Install it, for example: sudo dnf install NetworkManager-{vpn_type}",
        )
