"""Check an OpenVPN client file (.ovpn) before importing it into NetworkManager.

`nmcli connection import type openvpn` accepts almost any file: options it does
not know are dropped without a word, files that do not exist are imported as
dangling paths, and options OpenVPN itself no longer accepts are kept. The
connection then fails, or works differently from what the file says. This
module reads the file the way NetworkManager-openvpn 1.12 and OpenVPN 2.7 do
and explains what will go wrong, before the import.

The lists below were measured on Fedora 45: each option was imported into a
temporary NetworkManager connection and compared with a file without it.

The file is only read. Private keys are never decoded and no line of the file
is copied into the result except option names and file names.
"""

from __future__ import annotations

import re
import shlex
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from vpn_doctor.i18n import _
from vpn_doctor.models.diagnostic import DiagnosticItem, DiagnosticSeverity

MAX_FILE_BYTES = 1024 * 1024
INLINE_TAGS = (
    "ca", "cert", "key", "extra-certs", "tls-auth", "tls-crypt", "tls-crypt-v2",
    "secret", "pkcs12", "crl-verify", "dh", "connection", "http-proxy-user-pass",
    "auth-user-pass",
)
# Options whose first argument is a file, unless the content is inline.
FILE_OPTIONS = (
    "ca", "cert", "key", "extra-certs", "tls-auth", "tls-crypt", "tls-crypt-v2",
    "secret", "pkcs12", "crl-verify",
)
CERTIFICATE_OPTIONS = ("ca", "cert", "extra-certs")

# Dropped by NetworkManager although they change how the tunnel behaves.
DROPPED_IMPORTANT = ("redirect-gateway", "route-nopull", "pull-filter", "dhcp-option",
                     "remote-cert-eku", "ncp-ciphers", "route-ipv6")
# Dropped by NetworkManager, without consequence: NetworkManager does the same
# job itself (DNS, routes, retries, privileges) or they only tune logging.
DROPPED_HARMLESS = frozenset({
    "auth-nocache", "auth-retry", "block-outside-dns", "down", "explicit-exit-notify",
    "fast-io", "group", "ignore-unknown-option", "mute",
    "mute-replay-warnings", "nobind", "persist-key", "persist-tun", "pull", "rcvbuf",
    "reneg-bytes", "resolv-retry", "route-delay", "route-method", "route-up",
    "script-security", "setenv", "sndbuf", "tls-exit", "topology", "tun-mtu-extra",
    "txqueuelen", "up", "user", "verb", "comp-noadapt", "connect-retry",
    "connect-retry-max", "down-pre", "hand-window", "key-method", "link-mtu", "passtos",
    "persist-remote-ip", "ping-timer-rem", "replay-window", "route-metric",
})
# Imported by NetworkManager (measured, or read from the plugin).
SUPPORTED = frozenset({
    "client", "dev", "dev-type", "tls-client", "key-direction", "allow-compression",
    "allow-pull-fqdn", "auth", "auth-user-pass", "ca", "cert",
    "cipher", "comp-lzo", "compress", "connect-timeout", "crl-verify", "data-ciphers",
    "data-ciphers-fallback", "extra-certs", "float", "fragment", "http-proxy",
    "http-proxy-retry", "ifconfig", "keepalive", "key", "keysize", "max-routes", "mssfix",
    "mtu-disc", "ns-cert-type", "ping", "ping-exit", "ping-restart", "pkcs12", "port",
    "proto", "push-peer-info", "remote", "remote-cert-tls", "remote-random",
    "remote-random-hostname", "reneg-sec", "route", "rport", "secret", "server-poll-timeout",
    "socks-proxy", "socks-proxy-retry", "tls-auth", "tls-cipher", "tls-crypt",
    "tls-crypt-v2", "tls-remote", "tls-version-max", "tls-version-min", "tun-ipv6",
    "tun-mtu", "verify-x509-name",
})
# 64-bit block ciphers: not available at all with OpenSSL 3 without its legacy
# provider (Fedora, RHEL 9, Debian 12...), except triple DES.
UNAVAILABLE_CIPHERS = re.compile(r"^(BF|DES(?!-EDE)|DESX|CAST5|RC2|IDEA|SEED)-", re.IGNORECASE)
WEAK_CIPHERS = re.compile(r"^DES-EDE", re.IGNORECASE)
WEAK_DIGESTS = {"md5", "md4", "none"}
EXPIRY_WARNING = timedelta(days=30)
PEM_CERTIFICATE = re.compile(
    r"-----BEGIN CERTIFICATE-----.+?-----END CERTIFICATE-----", re.DOTALL
)


@dataclass(frozen=True)
class Option:
    name: str
    args: tuple[str, ...]
    line: int


@dataclass
class OvpnFile:
    """Options in file order and inline blocks, e.g. inline["ca"]."""

    options: list[Option] = field(default_factory=list)
    inline: dict[str, str] = field(default_factory=dict)
    # Line numbers that cannot be part of a valid file, and an inline block
    # that is never closed (it swallows the rest of the file).
    damaged_lines: list[int] = field(default_factory=list)
    unclosed: str | None = None

    def get(self, name: str) -> Option | None:
        return next((option for option in self.options if option.name == name), None)

    def has(self, name: str) -> bool:
        return self.get(name) is not None


@dataclass(frozen=True)
class CertificateInfo:
    """What matters in a certificate for OpenSSL 3 and system crypto policies."""

    subject: str
    key_type: str          # rsa, dsa, ec, ed25519...
    key_bits: int
    signature: str         # e.g. sha256WithRSAEncryption
    not_before: datetime
    not_after: datetime
    self_signed: bool


def parse_ovpn(text: str) -> OvpnFile:
    """Parse an OpenVPN config: options, arguments and <tag>...</tag> blocks."""
    result = OvpnFile()
    inline_tag: str | None = None
    inline_lines: list[str] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if inline_tag is not None:
            if line.lower() == f"</{inline_tag}>":
                result.inline[inline_tag] = "\n".join(inline_lines)
                inline_tag, inline_lines = None, []
            else:
                inline_lines.append(raw)
            continue
        opening = re.fullmatch(r"<([a-z0-9-]+)>", line, re.IGNORECASE)
        if opening:
            inline_tag = opening.group(1).lower()
            continue
        if not line or line[0] in "#;":
            continue
        if re.match(r"(<<<<<<<|=======|>>>>>>>|</)", line) or line.endswith(".ovpn"):
            result.damaged_lines.append(number)
            continue
        try:
            words = shlex.split(line, comments=True)
        except ValueError:
            words = line.split()
        if words:
            name = words[0].lower().removeprefix("--")
            result.options.append(Option(name, tuple(words[1:]), number))
    result.unclosed = inline_tag
    return result


def parse_openssl_date(value: str) -> datetime:
    """Parse "Nov 10 08:00:00 2026 GMT" as printed by `openssl x509 -dates`."""
    return datetime.strptime(" ".join(value.split()), "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC)


def inspect_certificate(pem: str) -> CertificateInfo | None:
    """Read one PEM certificate with the openssl command; None if it cannot."""
    try:
        completed = subprocess.run(
            ["openssl", "x509", "-noout", "-text", "-dates", "-subject", "-issuer",
             "-nameopt", "RFC2253"],
            input=pem, capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    text = completed.stdout
    fields = dict(re.findall(r"^(notBefore|notAfter|subject|issuer)=(.*)$", text, re.MULTILINE))
    key = re.search(r"Public Key Algorithm: (\S+)", text)
    bits = re.search(r"Public-Key: \((\d+) bit\)", text)
    signature = re.search(r"Signature Algorithm: (\S+)", text)
    try:
        not_before = parse_openssl_date(fields["notBefore"])
        not_after = parse_openssl_date(fields["notAfter"])
    except (KeyError, ValueError):
        return None
    key_name = key.group(1) if key else ""
    key_type = {"rsaEncryption": "rsa", "dsaEncryption": "dsa", "id-ecPublicKey": "ec"}.get(
        key_name, key_name.lower()
    )
    return CertificateInfo(
        subject=fields.get("subject", ""),
        key_type=key_type,
        key_bits=int(bits.group(1)) if bits else 0,
        signature=signature.group(1) if signature else "",
        not_before=not_before,
        not_after=not_after,
        self_signed=fields.get("subject") == fields.get("issuer"),
    )


class OvpnChecker:
    """Explain what NetworkManager and OpenVPN will do with an .ovpn file."""

    def __init__(
        self,
        inspect: Callable[[str], CertificateInfo | None] = inspect_certificate,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.inspect = inspect
        self.now = now

    def check_file(self, path: Path) -> list[DiagnosticItem]:
        """Raises OSError when the file cannot be read."""
        if path.stat().st_size > MAX_FILE_BYTES:
            return [_error(_("File"), _("This file is too large to be an OpenVPN configuration."))]
        text = path.read_text(encoding="utf-8", errors="replace")
        return self.check(parse_ovpn(text), path.parent)

    def check(self, config: OvpnFile, base_dir: Path) -> list[DiagnosticItem]:
        items: list[DiagnosticItem] = []
        items += self._structure(config)
        items += self._removed_options(config)
        items += self._files(config, base_dir)
        items += self._ciphers(config)
        items += self._compression(config)
        items += self._server_identity(config)
        items += self._tls(config)
        items += self._dropped(config)
        items += self._certificates(config, base_dir)
        if not any(item.severity != DiagnosticSeverity.INFO for item in items):
            items.insert(0, DiagnosticItem(
                name=_("Import"),
                success=True,
                message=_("Nothing in this file should prevent NetworkManager from using it."),
                severity=DiagnosticSeverity.INFO,
            ))
        return items

    # Each check returns the items it found, most serious first.

    @staticmethod
    def _structure(config: OvpnFile) -> list[DiagnosticItem]:
        items = []
        if config.unclosed:
            items.append(_error(
                _("Damaged file"),
                _(
                    "The <{tag}> block is never closed: everything after it is ignored."
                ).format(tag=config.unclosed),
                _("Add the missing </{tag}> line, or ask for the file again.").format(
                    tag=config.unclosed
                ),
            ))
        if config.damaged_lines:
            items.append(_warning(
                _("Damaged file"),
                _(
                    "Lines {lines} cannot belong to an OpenVPN file (merge conflict markers, "
                    "stray closing tags or file names). They are ignored."
                ).format(lines=", ".join(map(str, config.damaged_lines[:10]))),
                _("Check these lines: part of the configuration may be missing or mixed up."),
            ))
        if not config.has("remote") and "connection" not in config.inline:
            items.append(_error(
                _("Server"),
                _("The file has no `remote` line: it does not say which server to connect to."),
                _("Ask the VPN provider for the client configuration file."),
            ))
        if config.has("secret") or "secret" in config.inline:
            items.append(_error(
                _("Static key"),
                _(
                    "The file uses a static key (`secret`) instead of certificates. OpenVPN 2.7 "
                    "deprecates this mode and refuses its weak ciphers."
                ),
                _("Ask the VPN administrator for a configuration with certificates (TLS mode)."),
            ))
        return items

    @staticmethod
    def _removed_options(config: OvpnFile) -> list[DiagnosticItem]:
        items = []
        if config.has("tls-remote"):
            items.append(_error(
                _("Removed option"),
                _(
                    "`tls-remote` was removed from OpenVPN 2.4. NetworkManager imports it, but "
                    "OpenVPN refuses to start with it."
                ),
                _(
                    "Replace it with `verify-x509-name <server name> name`, or set the server "
                    "name in the TLS authentication settings of the connection after import."
                ),
            ))
        if config.has("ns-cert-type"):
            items.append(_warning(
                _("Deprecated option"),
                _("`ns-cert-type` is deprecated and checks an obsolete certificate extension."),
                _("Replace it with `remote-cert-tls server`."),
            ))
        return items

    @staticmethod
    def _files(config: OvpnFile, base_dir: Path) -> list[DiagnosticItem]:
        items = []
        for name in FILE_OPTIONS:
            option = config.get(name)
            if option is None or name in config.inline or not option.args:
                continue
            reference = option.args[0]
            if reference == "[inline]":
                continue
            target = Path(reference).expanduser()
            if not target.is_absolute():
                target = base_dir / target
            if not target.is_file():
                file_name = Path(reference).name
                if Path(reference).is_absolute() and (base_dir / file_name).is_file():
                    suggestion = _(
                        "{file} is next to the configuration: replace the path with just "
                        "`{file}` in the `{option}` line before importing."
                    ).format(file=file_name, option=name)
                else:
                    suggestion = _(
                        "Put the file next to the .ovpn file and use just its name in the "
                        "`{option}` line, or ask the VPN provider for a configuration with "
                        "inline certificates."
                    ).format(option=name)
                items.append(_error(
                    _("Missing file"),
                    _(
                        "`{option}` points to {file}, which does not exist. NetworkManager "
                        "imports the path anyway and the connection will fail."
                    ).format(option=name, file=file_name),
                    suggestion,
                ))
        return items

    @staticmethod
    def _ciphers(config: OvpnFile) -> list[DiagnosticItem]:
        names: list[str] = []
        for option_name in ("cipher", "data-ciphers", "data-ciphers-fallback", "ncp-ciphers"):
            option = config.get(option_name)
            if option and option.args:
                names += [name for name in option.args[0].split(":") if name]
        unavailable = sorted({name for name in names if UNAVAILABLE_CIPHERS.match(name)})
        weak = sorted({name for name in names if WEAK_CIPHERS.match(name)})
        items = []
        if unavailable:
            items.append(_error(
                _("Data cipher"),
                _(
                    "The file asks for {ciphers}, which OpenVPN can no longer use with "
                    "OpenSSL 3: these old 64-bit block ciphers are only in its legacy provider."
                ).format(ciphers=", ".join(unavailable)),
                _(
                    "Ask the VPN provider to enable AES-256-GCM on the server and remove the "
                    "old cipher from the file."
                ),
            ))
        if weak:
            items.append(_warning(
                _("Data cipher"),
                _(
                    "The file asks for {ciphers}: triple DES still works but is deprecated "
                    "(64-bit blocks, vulnerable to SWEET32 on long sessions)."
                ).format(ciphers=", ".join(weak)),
                _("Ask the VPN provider to enable AES-256-GCM on the server."),
            ))
        auth = config.get("auth")
        if auth and auth.args and auth.args[0].lower() in WEAK_DIGESTS:
            items.append(_warning(
                _("Packet authentication"),
                _("The file authenticates packets with {digest}, which is weak.").format(
                    digest=auth.args[0]
                ),
                _("Ask the VPN provider to use SHA256 or an AEAD cipher such as AES-256-GCM."),
            ))
        return items

    @staticmethod
    def _compression(config: OvpnFile) -> list[DiagnosticItem]:
        comp_lzo = config.get("comp-lzo")
        compress = config.get("compress")
        enabled = (comp_lzo is not None and (not comp_lzo.args or comp_lzo.args[0] != "no")) or (
            compress is not None and bool(compress.args) and not compress.args[0].startswith("stub")
        )
        if not enabled:
            return []
        return [_warning(
            _("Compression"),
            _(
                "The file turns compression on. Recent OpenVPN versions refuse it by default "
                "because compressing encrypted traffic can leak its content (VORACLE); if the "
                "server insists, the connection fails."
            ),
            _(
                "Ask the VPN provider to disable compression. Removing `comp-lzo` / `compress` "
                "from the file only works if the server does not require it."
            ),
        )]

    @staticmethod
    def _server_identity(config: OvpnFile) -> list[DiagnosticItem]:
        checked = any(config.has(name) for name in (
            "remote-cert-tls", "verify-x509-name", "ns-cert-type", "tls-remote",
        ))
        if checked or config.has("secret"):
            return []
        return [_warning(
            _("Server identity"),
            _(
                "The file never checks that the server certificate is a server certificate "
                "(`remote-cert-tls server`): another client of the same VPN could impersonate "
                "the server."
            ),
            _("Add `remote-cert-tls server` to the file before importing it."),
        )]

    @staticmethod
    def _tls(config: OvpnFile) -> list[DiagnosticItem]:
        items = []
        tls_auth = config.get("tls-auth")
        if (tls_auth or "tls-auth" in config.inline) and not config.has("key-direction"):
            has_direction = tls_auth is not None and len(tls_auth.args) >= 2
            if not has_direction:
                items.append(_warning(
                    _("TLS key"),
                    _(
                        "The file uses a `tls-auth` key without a key direction. Most servers "
                        "expect 1 on clients; with the wrong direction, the server never answers."
                    ),
                    _("Add `key-direction 1` to the file, unless the provider says otherwise."),
                ))
        tls_max = config.get("tls-version-max")
        if tls_max and tls_max.args and tls_max.args[0] in {"1.0", "1.1"}:
            items.append(_error(
                _("TLS version"),
                _(
                    "The file limits TLS to version {version}, which the system refuses."
                ).format(version=tls_max.args[0]),
                _("Remove `tls-version-max` and ask the provider to enable TLS 1.2 or newer."),
            ))
        return items

    @staticmethod
    def _dropped(config: OvpnFile) -> list[DiagnosticItem]:
        items = []
        explanations = {
            "redirect-gateway": (
                _(
                    "`redirect-gateway` is ignored by NetworkManager: unless the server pushes "
                    "it, only the VPN's own networks go through the tunnel, not all traffic."
                ),
                _(
                    "After import, check that \"Use this connection only for resources on its "
                    "network\" is off in the IPv4 and IPv6 settings, then verify your public "
                    "address once connected."
                ),
            ),
            "route-nopull": (
                _(
                    "`route-nopull` is ignored by NetworkManager: the routes pushed by the "
                    "server are applied anyway."
                ),
                _(
                    "After import, turn on \"Ignore automatically obtained routes\" in the IPv4 "
                    "routes settings of the connection."
                ),
            ),
            "pull-filter": (
                _(
                    "`pull-filter` is ignored by NetworkManager: settings the file wanted to "
                    "refuse from the server (routes, DNS...) are applied anyway."
                ),
                _(
                    "After import, ignore automatic routes or DNS in the IPv4 and IPv6 settings "
                    "if that was the goal."
                ),
            ),
            "dhcp-option": (
                _(
                    "`dhcp-option` in the file is ignored by NetworkManager: only the DNS "
                    "servers pushed by the VPN server are used."
                ),
                _("After import, add the DNS servers in the IPv4 settings of the connection."),
            ),
            "ncp-ciphers": (
                _(
                    "`ncp-ciphers` is the old name of `data-ciphers` (renamed in OpenVPN 2.5) and "
                    "NetworkManager ignores it: the default data ciphers are used instead."
                ),
                _("Rename `ncp-ciphers` to `data-ciphers` in the file before importing."),
            ),
            "route-ipv6": (
                _(
                    "`route-ipv6` is ignored by NetworkManager: these IPv6 routes are not added."
                ),
                _("After import, add the IPv6 routes in the IPv6 settings of the connection."),
            ),
            "remote-cert-eku": (
                _(
                    "`remote-cert-eku` is ignored by NetworkManager: this check of the server "
                    "certificate is lost."
                ),
                _(
                    "Make sure `remote-cert-tls server` or `verify-x509-name` is also in the "
                    "file, so the server is still verified."
                ),
            ),
        }
        for name in DROPPED_IMPORTANT:
            if config.has(name):
                message, suggestion = explanations[name]
                items.append(_warning(_("Ignored by NetworkManager"), message, suggestion))

        unknown = sorted({
            option.name for option in config.options
            if option.name not in SUPPORTED
            and option.name not in DROPPED_HARMLESS
            and option.name not in DROPPED_IMPORTANT
        })
        if unknown:
            items.append(DiagnosticItem(
                name=_("Ignored by NetworkManager"),
                success=True,
                message=_(
                    "NetworkManager does not import these options: {options}. Check that none "
                    "of them matters for this VPN."
                ).format(options=", ".join(unknown)),
                severity=DiagnosticSeverity.INFO,
            ))
        if "auth-user-pass" in config.inline or "http-proxy-user-pass" in config.inline:
            items.append(_warning(
                _("Password in the file"),
                _(
                    "The file contains a user name and a password in clear text. NetworkManager "
                    "does not import them, but anyone who can read this file can."
                ),
                _(
                    "Enter the password when NetworkManager asks for it, then delete this copy "
                    "of the file or remove the <auth-user-pass> block from it."
                ),
            ))
        elif config.has("auth-user-pass") and config.get("auth-user-pass").args:
            items.append(DiagnosticItem(
                name=_("Password"),
                success=True,
                message=_(
                    "The password file named by `auth-user-pass` is not imported: NetworkManager "
                    "asks for the password and keeps it in the keyring."
                ),
                severity=DiagnosticSeverity.INFO,
            ))
        return items

    def _certificates(self, config: OvpnFile, base_dir: Path) -> list[DiagnosticItem]:
        items = []
        now = self.now()
        for name in CERTIFICATE_OPTIONS:
            pem = config.inline.get(name)
            if pem is None:
                option = config.get(name)
                if option is None or not option.args:
                    continue
                target = Path(option.args[0]).expanduser()
                target = target if target.is_absolute() else base_dir / target
                try:
                    if not target.is_file() or target.stat().st_size > MAX_FILE_BYTES:
                        continue
                    pem = target.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
            per_certificate = [
                self._certificate_items(name, info, now)
                for info in map(self.inspect, PEM_CERTIFICATE.findall(pem))
                if info is not None
            ]
            usable = [found for found in per_certificate if not _has_error(found)]
            if name != "cert" and usable and len(usable) < len(per_certificate):
                # A CA bundle often keeps an old, expired CA next to its
                # replacement: OpenVPN uses whichever one signed the server.
                for found in usable:
                    items += found
                items.append(DiagnosticItem(
                    name=_("Old certificates"),
                    success=True,
                    message=_(
                        "`{option}` also contains expired or weak certificates next to valid "
                        "ones. OpenVPN uses the valid ones, so this is harmless."
                    ).format(option=name),
                    severity=DiagnosticSeverity.INFO,
                ))
            else:
                for found in per_certificate:
                    items += found
        return items

    @staticmethod
    def _certificate_items(
        option: str, info: CertificateInfo, now: datetime
    ) -> list[DiagnosticItem]:
        items = []
        label = _("`{option}` certificate {subject}").format(option=option, subject=info.subject)
        if info.not_after < now:
            items.append(_error(
                _("Expired certificate"),
                _("{label} expired on {date}.").format(label=label, date=info.not_after.date()),
                _("Ask the VPN provider for an up-to-date configuration."),
            ))
        elif info.not_before > now:
            items.append(_error(
                _("Certificate not valid yet"),
                _("{label} is only valid from {date}.").format(
                    label=label, date=info.not_before.date()
                ),
                _("Check the date and time of this computer."),
            ))
        elif info.not_after - now < EXPIRY_WARNING:
            items.append(_warning(
                _("Certificate expires soon"),
                _("{label} expires on {date}.").format(label=label, date=info.not_after.date()),
                _("Ask the VPN provider when it will be renewed."),
            ))
        if info.key_type in {"rsa", "dsa"} and 0 < info.key_bits < 2048:
            items.append(_error(
                _("Weak certificate"),
                _(
                    "{label} uses a {bits}-bit {type} key, which the system's cryptographic "
                    "policy refuses (2048 bits minimum)."
                ).format(label=label, bits=info.key_bits, type=info.key_type.upper()),
                _("Ask the VPN provider for new certificates (RSA 2048 bits or more)."),
            ))
        # The signature of a self-signed trust anchor is never checked.
        weak_signature = re.match(r"(md5|md4|sha1)", info.signature, re.IGNORECASE)
        if weak_signature and not info.self_signed:
            items.append(_error(
                _("Weak certificate"),
                _(
                    "{label} is signed with {algorithm}, which the system's cryptographic "
                    "policy refuses."
                ).format(label=label, algorithm=weak_signature.group(1).upper()),
                _("Ask the VPN provider for certificates signed with SHA-256."),
            ))
        return items


def _has_error(items: list[DiagnosticItem]) -> bool:
    return any(item.severity == DiagnosticSeverity.ERROR for item in items)


def _error(name: str, message: str, suggestion: str | None = None) -> DiagnosticItem:
    return DiagnosticItem(name, False, message, suggestion, DiagnosticSeverity.ERROR)


def _warning(name: str, message: str, suggestion: str | None = None) -> DiagnosticItem:
    return DiagnosticItem(name, False, message, suggestion, DiagnosticSeverity.WARNING)


def check_ovpn(path: Path) -> list[DiagnosticItem]:
    """Check an .ovpn file; raises OSError when it cannot be read."""
    return OvpnChecker().check_file(path)
