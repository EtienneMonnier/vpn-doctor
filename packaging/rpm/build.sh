#!/bin/sh
# Build the RPM from the current commit, in a private rpmbuild tree.
#   packaging/rpm/build.sh              normal package
#   packaging/rpm/build.sh --wasteland  Wasteland Terminal skin by default and
#                                       a terminal app icon, made from the local
#                                       image assets/icons/vpn-doctor-terminal.png
#                                       (not in the repository)
# Requires: rpm-build, pyproject-rpm-macros, python3-setuptools,
#           desktop-file-utils, appstream, gettext (see BuildRequires in the spec),
#           and ImageMagick for --wasteland.
set -eu

repo=$(git rev-parse --show-toplevel)
version=$(sed -n 's/^Version: *//p' "$repo/packaging/rpm/vpn-doctor.spec")
topdir=${RPM_TOPDIR:-$repo/build/rpm}
with=""

mkdir -p "$topdir/SOURCES"
git -C "$repo" archive --prefix="vpn-doctor-$version/" \
    -o "$topdir/SOURCES/vpn-doctor-$version.tar.gz" HEAD

if [ "${1:-}" = "--wasteland" ]; then
    image="$repo/assets/icons/vpn-doctor-terminal.png"
    if [ ! -f "$image" ]; then
        echo "Missing $image" >&2
        exit 1
    fi
    art=$(mktemp -d)
    trap 'rm -rf "$art"' EXIT
    magick "$image" -trim +repage -resize 1024x1024 -gravity center \
        -background none -extent 1024x1024 "$art/square.png"
    for size in 16 24 32 48 64 128 256 512; do
        mkdir -p "$art/icons/hicolor/${size}x${size}/apps"
        magick "$art/square.png" -filter Lanczos -resize "${size}x${size}" -strip \
            "$art/icons/hicolor/${size}x${size}/apps/io.github.vpndoctor.VPNDoctor.png"
    done
    magick "$art/square.png" -resize 440x440 -strip "$art/logo-terminal.png"
    tar -czf "$topdir/SOURCES/vpn-doctor-wasteland-art.tar.gz" -C "$art" icons logo-terminal.png
    with="--with wasteland"
fi

# shellcheck disable=SC2086
rpmbuild --define "_topdir $topdir" $with -ba "$repo/packaging/rpm/vpn-doctor.spec"
find "$topdir/RPMS" "$topdir/SRPMS" -name '*.rpm' -newer "$topdir/SOURCES/vpn-doctor-$version.tar.gz"
