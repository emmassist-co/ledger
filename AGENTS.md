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

## Archive guides

- The generic archive-building skill lives at [skills/archive-index-builder/SKILL.md](/Users/alexandre/dev/parliament/skills/archive-index-builder/SKILL.md).
- The current local archive operator guide lives at [archive-index/AGENTS.md](/Users/alexandre/dev/parliament/archive-index/AGENTS.md).
