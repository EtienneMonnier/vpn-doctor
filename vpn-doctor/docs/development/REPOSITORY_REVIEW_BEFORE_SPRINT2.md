# Repository Review Before Sprint 2

## Review summary

The repository has a good foundation:

- clear project identity;
- good package layout;
- basic CLI entry point;
- backend abstraction;
- OpenFortiVPN skeleton;
- first tests.

## Issues corrected in this pack

- Removed generated Python metadata from the deliverable.
- Removed empty accidental root-level `src/*` folders outside `src/vpn_doctor`.
- Expanded architecture documentation.
- Added Sprint 2 design specifications.
- Added additional ADRs.
- Strengthened security and secret-handling guidance.
- Added documentation index improvements.

## Recommended next commit

```text
docs: add Sprint 2 architecture and backend specifications
```

or, if code and docs are committed together:

```text
feat: prepare Sprint 2 OpenFortiVPN backend design
```

## Before committing

Run:

```bash
git status
git diff --stat
python -m pip install -e ".[dev]"
pytest
vpn-doctor --version
vpn-doctor diagnose
```
