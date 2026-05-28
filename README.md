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
- `skills/domain-archive-pack-builder/`: meta workflow for generating archive-local domain-pack contracts, recipes, and operator skills
- `src/ledger/archive_index/`: archive artifact and navigation code
- `examples/`: committed tiny archives used as regression fixtures

Current committed benchmark view:

- [examples/benchmark-summary.md](examples/benchmark-summary.md)

This repo is archive-first. The old transcript-processing pipeline is intentionally gone; the repo now focuses on archive scaffolding, rebuilds, verification, and evals.

Domain packs are the main way Ledger teaches future agents how to operate a bounded archive. They define canonical source families, persistence posture, confidence posture, refresh behavior, and user-escalation rules without turning Ledger into a heavyweight runtime.

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
uv run ledger eval summarize-examples examples
```

The eval runner reports:

- policy and grounding checks
- ranked retrieval metrics such as `hit@k`, `precision@k`, `recall@k`, `mrr@k`, and `ndcg@k`
- replay-style trajectory metrics such as completion pass rate, clean pass rate, drift rate, and median trace steps

If an example archive has `archive-evals/thresholds.json`, `ledger eval run` fails on threshold regressions.
