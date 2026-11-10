# rpmbuild --with wasteland: Wasteland Terminal skin by default and a terminal
# app icon, built from a local image that is not part of the repository
# (packaging/rpm/build.sh --wasteland).
%bcond wasteland 0

Name:           vpn-doctor
Version:        0.3.0
Release:        1%{?with_wasteland:.wasteland}%{?dist}
Summary:        Linux VPN troubleshooting and connection assistant

License:        MIT
URL:            https://github.com/EtienneMonnier/vpn-doctor
Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz
%if %{with wasteland}
Source1:        %{name}-wasteland-art.tar.gz
%endif

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  desktop-file-utils
BuildRequires:  appstream
BuildRequires:  gettext

Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita >= 1.5
Requires:       libsecret
Requires:       NetworkManager
Requires:       polkit
Requires:       iproute
Recommends:     openfortivpn
Recommends:     nm-connection-editor
Recommends:     systemd-resolved

%description
VPN Doctor is a companion to NetworkManager. It connects the VPNs you already
use and explains what goes wrong: failures from the NetworkManager reason and
the VPN plugin log, conflicts between VPNs and with the local network, Remote
Desktop servers behind the VPN. It can also run openfortivpn directly through
a small privileged helper, keeps secrets in the desktop keyring and supports
custom skins.

%prep
%autosetup -n %{name}-%{version}
%if %{with wasteland}
# Terminal app icon and logo, then the Wasteland skin by default.
tar -xzf %{SOURCE1} -C src/vpn_doctor/ui/assets
sed -i 's/^DEFAULT_SKIN = .*/DEFAULT_SKIN = "wasteland"/' src/vpn_doctor/branding.py
sed -i 's/@logo: logo-wasteland.svg/@logo: logo-terminal.png/' src/vpn_doctor/ui/themes/wasteland.css
%endif

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files vpn_doctor

po/compile.sh %{buildroot}%{_datadir}/locale
%find_lang %{name}

# The only code running as root (ADR-0012), with its polkit action.
install -Dpm 0755 src/vpn_doctor/privileged_helper.py \
    %{buildroot}%{_libexecdir}/vpn-doctor/vpn-doctor-helper
install -Dpm 0644 data/io.github.vpndoctor.helper.policy \
    %{buildroot}%{_datadir}/polkit-1/actions/io.github.vpndoctor.helper.policy
# Gateways approved by an administrator (ADR-0013), written by the helper.
install -dm 0755 %{buildroot}%{_sysconfdir}/vpn-doctor

install -Dpm 0644 data/io.github.vpndoctor.VPNDoctor.desktop \
    %{buildroot}%{_datadir}/applications/io.github.vpndoctor.VPNDoctor.desktop
install -Dpm 0644 data/io.github.vpndoctor.VPNDoctor.metainfo.xml \
    %{buildroot}%{_metainfodir}/io.github.vpndoctor.VPNDoctor.metainfo.xml
for size in 16 24 32 48 64 128 256 512; do
    install -Dpm 0644 \
        src/vpn_doctor/ui/assets/icons/hicolor/${size}x${size}/apps/io.github.vpndoctor.VPNDoctor.png \
        %{buildroot}%{_datadir}/icons/hicolor/${size}x${size}/apps/io.github.vpndoctor.VPNDoctor.png
done

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/io.github.vpndoctor.VPNDoctor.desktop
appstreamcli validate --no-net %{buildroot}%{_metainfodir}/io.github.vpndoctor.VPNDoctor.metainfo.xml
%pyproject_check_import -e 'vpn_doctor.ui*'

%files -f %{pyproject_files} -f %{name}.lang
%license LICENSE
%doc README.md CHANGELOG.md
%{_bindir}/vpn-doctor
%{_bindir}/vpn-doctor-gui
%dir %{_libexecdir}/vpn-doctor
%{_libexecdir}/vpn-doctor/vpn-doctor-helper
%{_datadir}/polkit-1/actions/io.github.vpndoctor.helper.policy
%dir %{_sysconfdir}/vpn-doctor
%ghost %config(noreplace) %{_sysconfdir}/vpn-doctor/gateways.json
%{_datadir}/applications/io.github.vpndoctor.VPNDoctor.desktop
%{_metainfodir}/io.github.vpndoctor.VPNDoctor.metainfo.xml
%{_datadir}/icons/hicolor/*/apps/io.github.vpndoctor.VPNDoctor.png

%changelog
* Tue Nov 10 2026 Etienne Monnier <128474711+EtienneMonnier@users.noreply.github.com> - 0.3.0-1
- OpenVPN: explain common failures (weak or expired certificates, legacy
  PKCS#12, TLS version, tls-auth/tls-crypt mismatch, ciphers, compression).
- New command check-ovpn: check an .ovpn file before importing it.

* Tue Nov 10 2026 Etienne Monnier <128474711+EtienneMonnier@users.noreply.github.com> - 0.2.0-1
- New shield logo and app icon; optional Wasteland build (--with wasteland).
- Translations in seven languages, --json on every CLI command, one tab per
  connection, latency checks, explanation of gateway login refusals.

* Thu Oct 29 2026 Etienne Monnier <128474711+EtienneMonnier@users.noreply.github.com> - 0.1.0-1
- First package: NetworkManager overlay, tabs, conflict detection, keyring
  secrets, privileged helper for openfortivpn, custom skins.
