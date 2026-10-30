#!/bin/sh
# Extract translatable strings into po/vpn-doctor.pot and merge them into
# every po/<lang>.po listed in po/LINGUAS. Run after changing user-visible text.
# Requires: gettext (xgettext, msgmerge, msginit).
set -eu

po=$(cd "$(dirname "$0")" && pwd)
repo=$(dirname "$po")
version=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$repo/src/vpn_doctor/__init__.py")

cd "$repo"
find src/vpn_doctor -name '*.py' ! -name privileged_helper.py | LC_ALL=C sort |
    xgettext --files-from=- --language=Python --from-code=UTF-8 \
        --keyword=_ --keyword=N_ --keyword=ngettext:1,2 \
        --add-comments=TRANSLATORS: --sort-by-file \
        --package-name=vpn-doctor --package-version="$version" \
        --msgid-bugs-address=https://github.com/EtienneMonnier/vpn-doctor/issues \
        --output="$po/vpn-doctor.pot"

for lang in $(cat "$po/LINGUAS"); do
    if [ -f "$po/$lang.po" ]; then
        msgmerge --quiet --update --backup=none --previous "$po/$lang.po" "$po/vpn-doctor.pot"
    else
        msginit --no-translator --locale="$lang" --input="$po/vpn-doctor.pot" --output-file="$po/$lang.po"
    fi
done
