# AGENTS.md

Canonical development guide for VPN Doctor.

Every AI assistant and contributor must follow this document before modifying the
project.

## Mission

VPN Doctor is not another VPN client.

It is a Linux VPN troubleshooting and connection assistant whose motto is:

**Diagnose. Connect. Protect.**

## Read order

Before coding, read:

1. `README.md`
2. `ARCHITECTURE.md`
3. `ROADMAP.md`
4. `docs/INDEX.md`
5. `docs/development/MASTER_ARCHITECTURE.md`
6. this file

## Non-negotiable rules

- GUI must never execute VPN binaries directly.
- Never store VPN passwords in source code or profile files.
- Never commit customer VPN addresses, usernames, fingerprints or logs unless sanitized.
- All user-visible strings must be prepared for gettext.
- Use Python logging instead of `print()` for internal logs.
- Keep backends independent from GTK.
- Keep models free from side effects.
- Prefer readable, boring code.

## Architecture rule

Use this flow:

```text
UI / CLI
  -> Controller
  -> Services
  -> Diagnostics / Backend Manager
  -> Backend
  -> Linux OS
```

## AI-specific rules

When working as an AI agent:

1. Inspect the current repository before generating code.
2. Do not assume missing files are intentionally absent.
3. Update documentation when changing architecture.
4. Add tests for non-trivial logic.
5. Do not introduce new dependencies unless justified.
6. Never hide uncertainty.
7. Avoid rewriting unrelated files.
8. Preserve the project philosophy: diagnosis before raw connection.

## Sprint discipline

Each sprint should include:

- specification;
- implementation plan;
- tests;
- documentation updates;
- changelog entry;
- review notes.

## Commit style

Use conventional commits:

- `feat:`
- `fix:`
- `docs:`
- `test:`
- `refactor:`
- `chore:`
- `ci:`

## Security

Never include:

- real passwords;
- live customer VPN endpoints;
- private keys;
- unredacted logs;
- certificate fingerprints tied to a real customer unless explicitly sanitized.

Use placeholders such as:

- `vpn.example.com`;
- `demo-user`;
- `abcdef...`;
- `192.0.2.0/24`.

## Long-term goal

VPN Doctor should become the Linux VPN troubleshooting assistant: backend-independent,
distribution-friendly, safe by default and useful for both beginners and system
administrators.
