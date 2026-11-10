# Packaging Guide

## Targets

| Target | Status |
| --- | --- |
| RPM (Fedora) | done: `packaging/rpm/vpn-doctor.spec`, published on COPR `etienne-monnier/vpn-doctor` |
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
| `/usr/share/icons/hicolor/<size>/apps/io.github.vpndoctor.VPNDoctor.png` | icon, 16 to 512 px |
| `/usr/share/locale/<lang>/LC_MESSAGES/vpn-doctor.mo` | translations, compiled from `po/` |

The helper and the policy must be installed together: the policy's
`org.freedesktop.policykit.exec.path` points at the helper's exact path.

## RPM

Build dependencies, once:

```bash
sudo dnf install rpm-build pyproject-rpm-macros python3-devel python3-setuptools \
    desktop-file-utils appstream gettext
```

Build from the current commit (sources come from `git archive HEAD`, so
commit first):

```bash
packaging/rpm/build.sh            # RPMs in build/rpm/RPMS and build/rpm/SRPMS
sudo dnf install ./build/rpm/RPMS/noarch/vpn-doctor-0.3.0-1.*.noarch.rpm
```

### Wasteland build

```bash
packaging/rpm/build.sh --wasteland   # vpn-doctor-0.3.0-1.wasteland.*.noarch.rpm
```

`rpmbuild --with wasteland` makes Wasteland Terminal the default skin
(`vpn_doctor/branding.py`) and replaces the app icon and the skin logo with a
terminal image. That image (`assets/icons/vpn-doctor-terminal.png`) stays
local: it is ignored by git and must not be published, since it resembles a
game's trade dress. The build script turns it into icons with ImageMagick.

Both builds are the same package name: installing one replaces the other
(going back from the Wasteland build needs `dnf reinstall` or `dnf downgrade`
because its release sorts higher). A skin the user already chose in
Preferences wins over the packaged default.

### Icons

The app icon and the default logo are made from `assets/icons/vpn-doctor.png`:

```bash
magick assets/icons/vpn-doctor.png -trim +repage -resize 1024x1024 -gravity center \
    -background none -extent 1024x1024 /tmp/square.png
for size in 16 24 32 48 64 128 256 512; do
    magick /tmp/square.png -filter Lanczos -resize ${size}x${size} -strip \
        src/vpn_doctor/ui/assets/icons/hicolor/${size}x${size}/apps/io.github.vpndoctor.VPNDoctor.png
done
magick /tmp/square.png -resize 440x440 -strip src/vpn_doctor/ui/assets/logo-default.png
```

`%check` validates the launcher and the AppStream file and imports the
non-GUI modules.

## COPR

Releases are published on https://copr.fedorainfracloud.org/coprs/etienne-monnier/vpn-doctor/
(Fedora 43, 44, 45 and rawhide; x86_64 and aarch64). Only the normal build,
never the Wasteland one.

```bash
# once: copr-cli installed, API token from https://copr.fedorainfracloud.org/api/
#       in ~/.config/copr (mode 600)
packaging/rpm/build.sh                      # from the release commit
copr-cli build vpn-doctor build/rpm/SRPMS/vpn-doctor-<version>-1.*.src.rpm
```

Tag the commit that was built (`git tag -a v<version>`), then bring `main` to
it. The token expires after 180 days.

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
