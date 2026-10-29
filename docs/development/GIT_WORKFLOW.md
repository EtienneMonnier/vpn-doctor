# Git Workflow

## Before the first public release

The project is developed directly on `dev`, without feature branches or pull
requests. Every commit on `dev` must still pass `ruff check src tests` and
`pytest`.

`main` only receives the first public release. The full flow below applies
from then on.

## After the first public release

### Branches

```text
main      stable releases
dev       integration
feature/* features
bugfix/*  bug fixes
hotfix/*  urgent stable fixes
```

### Flow

```text
feature/* -> Pull Request -> dev -> Pull Request -> main -> tag
```

## Commit examples

```text
feat: add OpenFortiVPN backend lifecycle
docs: document OpenFortiVPN state machine
test: add log parser tests
fix: avoid leaking usernames in logs
```
