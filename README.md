# Ledger

Agent-native archive toolkit for building, growing, and verifying evidence-first compounding indexes.

This repository tracks the reusable workflow, skills, prompts, code, and tests.
The live `archive-index/` workspace is intentionally excluded from Git and treated as local generated/runtime state.

Start with [GETTING_STARTED.md](GETTING_STARTED.md) for the shortest path from install to a working archive.

## Usage

```bash
uv run ledger --help
```

Core repo surfaces:

- `skills/archive-index-builder/`: archive creation and growth workflow
- `skills/archive-evals/`: eval workflow for archive reliability and boundary behavior
- `src/ledger/archive_index/`: archive artifact and navigation code
- `examples/`: committed tiny archives used as regression fixtures

This repo is archive-first. The old transcript-processing pipeline is intentionally gone; the repo now focuses on archive scaffolding, rebuilds, verification, and evals.

## Principles

Start with [PRINCIPLES.md](PRINCIPLES.md) for the design boundary Ledger is enforcing.

## Environment

Ledger core does not require a runtime API key.

Use [.env.example](.env.example) only if a specific archive workspace later needs credentials for its own local source access or fetch workflow.

## CLI

Scaffold a new archive workspace:

```bash
uv run ledger archive scaffold /tmp/my-archive
```

Rebuild its navigation index:

```bash
uv run ledger archive rebuild-index --root /tmp/my-archive
```

Generate and run evals:

```bash
uv run ledger eval generate-corpus /tmp/my-archive --limit 6
uv run ledger eval run /tmp/my-archive
```

The eval runner reports both policy/grounding checks and ranked retrieval metrics such as `hit@k`, `precision@k`, `recall@k`, `mrr@k`, and `ndcg@k`.
