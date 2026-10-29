Name:           vpn-doctor
Version:        0.1.0
Release:        1%{?dist}
Summary:        Linux VPN troubleshooting and connection assistant

License:        MIT
URL:            https://github.com/EtienneMonnier/vpn-doctor
Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  desktop-file-utils
BuildRequires:  appstream

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

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files vpn_doctor

# The only code running as root (ADR-0012), with its polkit action.
install -Dpm 0755 src/vpn_doctor/privileged_helper.py \
    %{buildroot}%{_libexecdir}/vpn-doctor/vpn-doctor-helper
install -Dpm 0644 data/io.github.vpndoctor.helper.policy \
    %{buildroot}%{_datadir}/polkit-1/actions/io.github.vpndoctor.helper.policy

install -Dpm 0644 data/io.github.vpndoctor.VPNDoctor.desktop \
    %{buildroot}%{_datadir}/applications/io.github.vpndoctor.VPNDoctor.desktop
install -Dpm 0644 data/io.github.vpndoctor.VPNDoctor.metainfo.xml \
    %{buildroot}%{_metainfodir}/io.github.vpndoctor.VPNDoctor.metainfo.xml
install -Dpm 0644 src/vpn_doctor/ui/assets/icons/hicolor/scalable/apps/io.github.vpndoctor.VPNDoctor.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/io.github.vpndoctor.VPNDoctor.svg

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/io.github.vpndoctor.VPNDoctor.desktop
appstreamcli validate --no-net %{buildroot}%{_metainfodir}/io.github.vpndoctor.VPNDoctor.metainfo.xml
%pyproject_check_import -e 'vpn_doctor.ui*'

%files -f %{pyproject_files}
%license LICENSE
%doc README.md CHANGELOG.md
%{_bindir}/vpn-doctor
%{_bindir}/vpn-doctor-gui
%dir %{_libexecdir}/vpn-doctor
%{_libexecdir}/vpn-doctor/vpn-doctor-helper
%{_datadir}/polkit-1/actions/io.github.vpndoctor.helper.policy
%{_datadir}/applications/io.github.vpndoctor.VPNDoctor.desktop
%{_metainfodir}/io.github.vpndoctor.VPNDoctor.metainfo.xml
%{_datadir}/icons/hicolor/scalable/apps/io.github.vpndoctor.VPNDoctor.svg

%changelog
* Thu Oct 29 2026 Etienne Monnier <etienne.monnier@quadronics.com> - 0.1.0-1
- First package: NetworkManager overlay, tabs, conflict detection, keyring
  secrets, privileged helper for openfortivpn, custom skins.
