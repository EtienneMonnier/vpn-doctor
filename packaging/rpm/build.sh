#!/bin/sh
# Build the RPM from the current commit, in a private rpmbuild tree.
# Requires: rpm-build, pyproject-rpm-macros, python3-setuptools,
#           desktop-file-utils, appstream (see BuildRequires in the spec).
set -eu

repo=$(git rev-parse --show-toplevel)
version=$(sed -n 's/^Version: *//p' "$repo/packaging/rpm/vpn-doctor.spec")
topdir=${RPM_TOPDIR:-$repo/build/rpm}

mkdir -p "$topdir/SOURCES"
git -C "$repo" archive --prefix="vpn-doctor-$version/" \
    -o "$topdir/SOURCES/vpn-doctor-$version.tar.gz" HEAD
rpmbuild --define "_topdir $topdir" -ba "$repo/packaging/rpm/vpn-doctor.spec"
find "$topdir/RPMS" "$topdir/SRPMS" -name '*.rpm' -newer "$topdir/SOURCES/vpn-doctor-$version.tar.gz"
