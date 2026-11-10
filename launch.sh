#!/bin/sh
# Run VPN Doctor from this checkout, without installing it.
#   ./launch.sh              start the GUI
#   ./launch.sh profiles     any CLI command: profiles, status, conflicts...
#
# Uses the system python3 (PyGObject, GTK 4, libadwaita and libsecret come
# from the distribution, not from the virtualenv).
cd "$(dirname "$0")" || exit 1
if [ "$#" -eq 0 ]; then
    set -- gui
fi
# Translations: compiled from po/ when gettext is installed, English otherwise.
if command -v msgfmt >/dev/null 2>&1 && po/compile.sh build/locale; then
    export VPN_DOCTOR_LOCALEDIR="$PWD/build/locale"
fi
PYTHONPATH=src exec python3 -m vpn_doctor.app "$@"
