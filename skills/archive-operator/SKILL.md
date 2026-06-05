---
name: archive-operator
description: Use when operating a local archive workspace to answer questions, audit answers, run archive checks, or propose expansion from official sources without bypassing the archive contract
---

# Archive Operator

Use the archive's local rules first.

## Required Reads

- local `AGENTS.md`
- local archive operator skill under `skills/`
- local `domain/DOMAIN.md` when present
- local `recipes/` files when present
- `references/consultation-runtime-contract.md` when using the consultation wrapper or reviewing consultation audit artifacts

## Workflow

1. Query the local archive before using external search.
2. Classify the task as `rule_lookup`, `case_application`, or `archive_audit`.
3. Use local generated scripts instead of improvising shell/plumbing steps.
4. Prefer `uv run python scripts/run_archive_check.py ...` for checks that need payload JSON or read recipe files.
5. If the answer depends on stronger local support than the archive currently has, either:
   - expand the archive from the known official source family, or
   - stop and say expansion is the next step.
6. Keep final answers aligned with the local answer contract and support hierarchy.

## Rules

- Do not pass inline JSON directly to scripts that expect a file path when the archive provides a wrapper helper.
- Default to `uv run python` for archive-local helper scripts unless the archive explicitly documents plain `python3` as sufficient.
- If a check uses archive recipes or support/confirmation logic, treat it as environment-backed and run it through `uv run python`.
- Treat `raw_source`, `extract`, and `derived_summary` as different evidence levels.
- Do not present a plausible case application as confirmed when blocking facts remain unresolved.
- If a gap is found and the official source family is known, say whether the next step is expansion, not generic browsing.
