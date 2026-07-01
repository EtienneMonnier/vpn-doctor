# Git Workflow

## Branches

```text
main
dev
feature/<name>
bugfix/<name>
hotfix/<name>
```

## Rules

- `main` must stay stable.
- `dev` is integration.
- Feature work happens on feature branches.
- Merge to `main` only when stable.

## Commit style

Use conventional commits:

```text
feat: add profile model
fix: detect untrusted certificate
docs: expand architecture guide
test: add route parser tests
ci: add Python workflow
```

## Pull requests

Every PR should include:

- summary
- test notes
- documentation impact
- screenshots for UI changes
