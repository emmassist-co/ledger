# Getting Started

`Ledger` is an agent-native archive toolkit for building and growing evidence-first archives without indexing everything up front.

## Install

```bash
uv sync
```

Create a `.env` only if a specific archive workspace later needs credentials for its own source access.
Keep live archives outside the Ledger repo. Prefer a sibling directory or standalone repo that consumes Ledger.

## Core Flow

1. Scaffold a new local archive workspace with the archive builder skill and scaffold script.
2. Add a domain pack when the archive needs domain-specific source, persistence, confidence, and refresh rules.
3. Query the archive first.
4. Expand only the missing slice from an in-bounds canonical source.
5. Persist official source material on use unless policy says to skip.
6. Rebuild the generated index.
7. Run verifier checks before treating the answer as grounded.
8. Let the archive remember what it learned through coverage-ledger state such as known gaps, provisional weak slices, partial topics, and stale topics.

## Minimal Archive Loop

Create a local archive workspace:

```bash
uv run ledger archive scaffold ../my-archive
```

Use the generated workspace from inside that archive repo:

```bash
cd ../my-archive
uv run ledger archive rebuild-source-indexes --root .
uv run ledger archive rebuild-index --root .
python3 scripts/archive_verifier.py check_policy . --action expand --autonomy-policy proactive
python3 scripts/check_index_consistency.py .
uv run ledger eval generate-corpus . --limit 6
uv run ledger eval run .
```

The eval report includes:

- retrieval metrics
- verifier outcomes
- replay-style trajectory metrics for the archive-answering path
- answer-quality posture metrics
- replay and false-completion proof lanes when scenarios define them
- threshold pass/fail when `archive-evals/thresholds.json` is present

## What Lives In Git

- Skills
- Scaffold scripts
- Verifier and eval tooling
- Package code under `src/ledger/`
- Tests

## What Does Not Live In Git

- Live archive workspaces such as `archive-index/`
- Generated index outputs
- Local source caches and manifests for a specific archive

Treat archives as local runtime state. Treat the toolkit as the versioned source of truth.

## Rules That Matter

- Do not hand-edit generated index files such as `documents.jsonl`, `links.jsonl`, or `navigation.sqlite`.
- Let the model write source artifacts and decision records; let scripts rebuild and verify generated state.
- Exact-wording claims should be backed by `raw_source` or `extract`, not only a summary.
- User-specific calculations should not become durable archive knowledge.

## Skills

- [skills/archive-index-builder/SKILL.md](skills/archive-index-builder/SKILL.md)
- [skills/archive-evals/SKILL.md](skills/archive-evals/SKILL.md)

## Committed Fixtures

Use [examples/README.md](examples/README.md) for committed small archives, including harder DR-derived fixtures that exercise cross-corpus grounding and exact-wording blocking.
