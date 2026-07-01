# AI Guidelines

## Purpose

This document helps AI assistants contribute consistently.

## Before coding

An AI agent must:

1. Inspect the repository tree.
2. Read `AGENTS.md`.
3. Read `ARCHITECTURE.md`.
4. Read the relevant development guide.
5. Avoid changing unrelated files.

## Rules

- Do not invent architecture.
- Do not bypass services.
- Do not put subprocess calls in UI code.
- Do not add dependencies without explaining why.
- Do not commit secrets.
- Prefer small patches.
- Update documentation when needed.

## Good AI task prompt

```text
Implement the OpenFortiVPN backend skeleton.
Follow AGENTS.md.
Do not implement GTK UI.
Add tests for log parsing.
Update BACKEND_GUIDELINES.md if needed.
```

## Bad AI task prompt

```text
Make the whole app.
```
