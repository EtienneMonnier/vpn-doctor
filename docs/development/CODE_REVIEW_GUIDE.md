# Code Review Guide

## Before merging

Check:

- tests pass;
- documentation updated;
- no secrets committed;
- no generated files committed;
- architecture respected;
- no GUI-to-backend direct subprocess calls.

## Common red flags

- `shell=True`;
- passwords in command arguments;
- real VPN data in fixtures;
- GTK imports inside backend modules;
- duplicated parsing logic.
