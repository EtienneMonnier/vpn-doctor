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
PYTHONPATH=src exec python3 -m vpn_doctor.app "$@"
