# Repository Agent Guide

## Working agreements

- Be sharp, short, and save tokens.
- If a task needs heavy refactor or paradigm change, ask first.
- Prefer clear, easy-to-reason code over backward-compatibility unless explicitly requested.
- Avoid touching large generated artifacts unless asked.

## Memory and search

- Use QMD as the primary memory/search system for notes, docs, and decisions.
- Prefer `qmd query` for hybrid search, `qmd search` for keyword search, and `qmd vsearch` for semantic search.

## Scope of this file

This file is for agents working on the `parliament` repository itself:

- repo code
- repo tests
- repo skills
- repo docs
- committed example fixtures

Do not treat this file as the operating guide for a live archive workspace.

## Archive workspace boundary

- A live local archive workspace such as `archive-index/` should carry its own local `AGENTS.md`.
- That workspace-local `AGENTS.md` is where archive operating policy belongs: corpus scope, autonomy, confidence bar, provenance expectations, enrichment posture, and navigation-index location.
- `examples/` are committed regression fixtures, not live operator workspaces. Do not infer general operating policy from them unless the task is explicitly about fixture design or eval coverage.

## Archive proof rule

When changing Ledger behavior that affects archive creation, archive operation, domain packs, evals, or verifier/checker behavior, do not treat unit tests alone as enough proof.

Use this proof ladder:

1. Run the relevant repo tests.
2. Run the relevant archive evals.
3. Run at least one real agent-style trial against the live local archive when the change affects archive operation, answer posture, enrichment, or safety boundaries.

The goal is to measure real progress, not only scaffolding correctness.

If the live archive exists, use it as an operational proving ground before claiming the workflow is working well.

## Archive guides

- The generic archive-building skill lives at [skills/archive-index-builder/SKILL.md](skills/archive-index-builder/SKILL.md).
- The live local `archive-index/` workspace is intentionally not part of the committed repo. Treat archive workspaces as generated local state, not as versioned source.
- The builder skill already defines what belongs in an archive workspace's local `AGENTS.md`; keep that guidance there rather than duplicating it in this repo-level file.
