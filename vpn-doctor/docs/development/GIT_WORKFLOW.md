# Git Workflow

## Branches

```text
main      stable releases
dev       integration
feature/* features
bugfix/*  bug fixes
hotfix/*  urgent stable fixes
```

## Flow

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
