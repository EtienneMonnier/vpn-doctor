#!/usr/bin/env bash
set -euo pipefail

echo "== VPN Doctor - Sprint 0 documentation commit =="

git status --short

echo
echo "Adding files..."
git add .

echo
echo "Creating commit..."
git commit -m "docs: establish Sprint 0 project foundation"

echo
echo "Pushing to origin/main..."
git push origin main

echo
echo "Creating tag v0.0.1-foundation..."
git tag -a v0.0.1-foundation -m "Foundation release - Sprint 0 documentation and architecture"

echo
echo "Pushing tag..."
git push origin v0.0.1-foundation

echo
echo "Done."
