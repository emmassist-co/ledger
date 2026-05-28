# Repository Agent Guide

## Working agreements

- Be sharp, short, and save tokens.
- If a task needs heavy refactor or paradigm change, ask first.
- Prefer clear, easy-to-reason code over backward-compatibility unless explicitly requested.
- Avoid touching large generated artifacts unless asked.

## Memory and search

- Use QMD as the primary memory/search system for notes, docs, and decisions.
- Prefer `qmd query` for hybrid search, `qmd search` for keyword search, and `qmd vsearch` for semantic search.

## Archive-first rule

When answering questions that may be served by the local archive:

1. Query the local archive first.
2. Use the archive navigation layer instead of scanning files blindly.
3. If coverage is thin, enrich the archive from the canonical official source for the missing slice.
4. Persist the new slice back into the archive.
5. Answer from the enriched archive.
6. Use broader web search only when the archive plus canonical-source path is insufficient or ambiguous.

Do not default to generic web search when an identifiable official source exists.

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
