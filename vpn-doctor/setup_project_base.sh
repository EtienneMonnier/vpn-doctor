#!/usr/bin/env bash
set -euo pipefail

mkdir -p \
  .github/ISSUE_TEMPLATE \
  .github/workflows \
  src/vpn_doctor/{ui,backend,diagnostics,models,services,utils} \
  tests \
  assets/{icons,images,screenshots} \
  packaging/{flatpak,rpm,deb}

touch \
  src/vpn_doctor/__init__.py \
  src/vpn_doctor/ui/__init__.py \
  src/vpn_doctor/backend/__init__.py \
  src/vpn_doctor/diagnostics/__init__.py \
  src/vpn_doctor/models/__init__.py \
  src/vpn_doctor/services/__init__.py \
  src/vpn_doctor/utils/__init__.py

cat > LICENSE <<'EOL'
MIT License

Copyright (c) 2026 Etienne Monnier

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
EOL

cat > CONTRIBUTING.md <<'EOL'
# Contributing to VPN Doctor

VPN Doctor is currently in early design and MVP development.

## Development rules

- Keep `main` stable.
- Work on `dev` or feature branches.
- Prefer small commits.
- Document important design decisions.
- Do not store VPN passwords, certificates, or private company data in the repository.
EOL

cat > CHANGELOG.md <<'EOL'
# Changelog

## Unreleased

- Initial project structure.
- Documentation draft.
- Planned MVP architecture.
EOL

cat > .github/pull_request_template.md <<'EOL'
## Summary

Describe the change.

## Checklist

- [ ] Code tested locally
- [ ] Documentation updated if needed
- [ ] No secrets committed
EOL

cat > .github/ISSUE_TEMPLATE/bug_report.md <<'EOL'
---
name: Bug report
about: Report a problem with VPN Doctor
title: "[Bug] "
labels: bug
---

## Description

## Steps to reproduce

## Expected behavior

## Logs

## Environment

- Distribution:
- Desktop environment:
- VPN backend:
EOL

cat > .github/ISSUE_TEMPLATE/feature_request.md <<'EOL'
---
name: Feature request
about: Suggest a new feature
title: "[Feature] "
labels: enhancement
---

## Feature

## Why it is useful

## Proposed behavior
EOL

cat > pyproject.toml <<'EOL'
[project]
name = "vpn-doctor"
version = "0.0.1"
description = "A Linux VPN troubleshooting and connection assistant."
readme = "README.md"
requires-python = ">=3.11"
license = "MIT"
authors = [
  { name = "Etienne Monnier" }
]
dependencies = []

[project.scripts]
vpn-doctor = "vpn_doctor.app:main"

[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
EOL

cat > src/vpn_doctor/app.py <<'EOL'
def main() -> None:
    print("VPN Doctor MVP placeholder")


if __name__ == "__main__":
    main()
EOL

cat > .github/workflows/python.yml <<'EOL'
name: Python checks

on:
  push:
    branches: [ main, dev ]
  pull_request:
    branches: [ main, dev ]

jobs:
  checks:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install package
        run: |
          python -m pip install --upgrade pip
          pip install -e .

      - name: Smoke test
        run: |
          vpn-doctor
EOL

git add .
git commit -m "Add project foundation files"

git checkout -b dev
git push -u origin dev
git checkout main

echo "Project base created."
