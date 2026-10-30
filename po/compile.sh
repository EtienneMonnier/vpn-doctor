#!/bin/sh
# Compile every po/<lang>.po into DESTDIR/<lang>/LC_MESSAGES/vpn-doctor.mo.
#   po/compile.sh build/locale            for launch.sh
#   po/compile.sh %{buildroot}/usr/share/locale    for packages
set -eu

po=$(cd "$(dirname "$0")" && pwd)
dest=${1:?usage: po/compile.sh DESTDIR}

for lang in $(cat "$po/LINGUAS"); do
    mkdir -p "$dest/$lang/LC_MESSAGES"
    msgfmt --check --output-file="$dest/$lang/LC_MESSAGES/vpn-doctor.mo" "$po/$lang.po"
done
