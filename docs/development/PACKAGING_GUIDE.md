# Packaging Guide

## Targets

| Target | Status |
| --- | --- |
| RPM (Fedora) | done: `packaging/rpm/vpn-doctor.spec` |
| DEB (Debian, Ubuntu) | planned, same file layout |
| Flatpak | not suitable today, see below |

## What a package installs

| File | Purpose |
| --- | --- |
| Python package `vpn_doctor` | the application |
| `/usr/bin/vpn-doctor`, `/usr/bin/vpn-doctor-gui` | CLI and GUI entry points |
| `/usr/libexec/vpn-doctor/vpn-doctor-helper` | privileged helper, mode 0755, root-owned (ADR-0012) |
| `/usr/share/polkit-1/actions/io.github.vpndoctor.helper.policy` | polkit actions connect, approve, revoke (ADR-0013) |
| `/etc/vpn-doctor/` | approved gateways, written by the helper |
| `/usr/share/applications/io.github.vpndoctor.VPNDoctor.desktop` | launcher |
| `/usr/share/metainfo/io.github.vpndoctor.VPNDoctor.metainfo.xml` | AppStream (GNOME Software) |
| `/usr/share/icons/hicolor/scalable/apps/io.github.vpndoctor.VPNDoctor.svg` | icon |

The helper and the policy must be installed together: the policy's
`org.freedesktop.policykit.exec.path` points at the helper's exact path.

## RPM

Build dependencies, once:

```bash
sudo dnf install rpm-build pyproject-rpm-macros python3-devel python3-setuptools \
    desktop-file-utils appstream
```

Build from the current commit (sources come from `git archive HEAD`, so
commit first):

```bash
packaging/rpm/build.sh            # RPMs in build/rpm/RPMS and build/rpm/SRPMS
sudo dnf install ./build/rpm/RPMS/noarch/vpn-doctor-0.1.0-1.*.noarch.rpm
```

`%check` validates the launcher and the AppStream file and imports the
non-GUI modules.

## DEB

Planned with the same layout. Runtime dependencies map to:
`python3-gi`, `gir1.2-gtk-4.0`, `gir1.2-adw-1` (libadwaita >= 1.5, Ubuntu
24.04 or Debian 13), `gir1.2-secret-1`, `network-manager`, `policykit-1`,
`iproute2`; recommends `openfortivpn`, `network-manager-gnome`.

## Flatpak

Not a good fit for now:

- the privileged helper must be installed on the host with its polkit
  policy; a Flatpak cannot ship either;
- `openfortivpn`, `ip`, `resolvectl` and the NetworkManager journal live on
  the host; reaching them needs `flatpak-spawn --host`, which would bypass the
  sandbox anyway.

A Flatpak may make sense later for a NetworkManager-only edition (D-Bus
access to NetworkManager and the Secret portal), without the openfortivpn
backend.
