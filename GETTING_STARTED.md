# Getting Started

`Ledger` is an agent-native archive toolkit for building and growing evidence-first archives without indexing everything up front.

## Install

```bash
uv sync
```

Create a `.env` only if a specific archive workspace later needs credentials for its own source access.

## Core Flow

1. Scaffold a new local archive workspace with the archive builder skill and scaffold script.
2. Query the archive first.
3. Expand only the missing slice from an in-bounds canonical source.
4. Persist official source material on use unless policy says to skip.
5. Rebuild the generated index.
6. Run verifier checks before treating the answer as grounded.

## Minimal Archive Loop

Create a local archive workspace:

```bash
uv run ledger archive scaffold /tmp/my-archive
```

Use the generated workspace:

```bash
uv run ledger archive rebuild-index --root /tmp/my-archive
python3 /tmp/my-archive/scripts/archive_verifier.py check_policy /tmp/my-archive --action expand --autonomy-policy proactive
python3 /tmp/my-archive/scripts/check_index_consistency.py /tmp/my-archive
uv run ledger eval generate-corpus /tmp/my-archive --limit 6
uv run ledger eval run /tmp/my-archive
```

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
