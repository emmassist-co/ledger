# Ledger

Agent-native archive toolkit for building, growing, and verifying evidence-first compounding indexes.

This repository tracks the reusable workflow, skills, prompts, code, and tests.
The live `archive-index/` workspace is intentionally excluded from Git and treated as local generated/runtime state.
Do not put a real archive workspace inside the Ledger repo. Create it as a sibling directory or its own repo that consumes Ledger.

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

Every generated archive should expose the same small practice layer:

- memory surfaces for known gaps, provisional weak slices, partial topics, and stale topics
- helper checks for coverage, support strength, pre-answer weakness, auto-expand policy, and confirmation boundaries
- proof surfaces for direct answer, expand-then-answer, ask-user, false completion, and replay-style closure

The goal is that a new index type needs new pack data and maybe a new source playbook, not a new theory of operation.

## Principles

Start with [PRINCIPLES.md](PRINCIPLES.md) for the design boundary Ledger is enforcing.

## Environment

Ledger core does not require a runtime API key.

Use [.env.example](.env.example) only if a specific archive workspace later needs credentials for its own local source access or fetch workflow.

## CLI

Scaffold a new archive workspace:

```bash
uv run ledger archive scaffold ../my-archive
```

Then work from the archive repo itself:

```bash
cd ../my-archive
uv run ledger archive rebuild-source-indexes --root .
uv run ledger archive rebuild-index --root .
uv run python scripts/run_archive_evals.py run .
```

Rebuild only its navigation index:

```bash
uv run ledger archive rebuild-index --root .
```

Rebuild the local source-side indexes after changing captured Markdown or extracted PDFs:

```bash
uv run ledger archive rebuild-source-indexes --root .
```

Capture a public webpage as Markdown instead of persisting raw HTML:

```bash
uv run ledger archive fetch-url \
  --root . \
  --source-id gov-pt-pedir-o-irs-jovem \
  --url https://www.gov.pt/servicos/pedir-o-irs-jovem
```

This uses `markdown.new` first and falls back to `r.jina.ai`, then writes the Markdown capture under `source/downloads/` and appends provenance to `source/manifests/downloads.jsonl`.

Extract and index a PDF by page so later searches can open only the relevant slices:

```bash
uv run ledger archive index-pdf \
  --root . \
  --source-id dar-i-016 \
  --pdf-path source/downloads/DAR-I-016.pdf \
  --source-url https://example.org/DAR-I-016.pdf \
  --title "DAR I 016"
```

Then search the page index instead of reading the whole PDF:

```bash
uv run ledger archive search-pdf \
  --root . \
  --query "salario minimo contrato" \
  --source-id dar-i-016
```

This uses `liteparse` as the PDF parser, writes layout-aware JSON plus per-page Markdown under `source/extracted/`, per-source page rows under `source/index/pdf-pages/`, and a shared FTS index at `source/index/pdf-pages.sqlite`.

Search a captured website by section instead of rereading the full Markdown:

```bash
uv run ledger archive search-web \
  --root . \
  --query "tornas IRS Anexo G partilha bens imoveis"
```

`fetch-url` auto-builds a thin section cache under `source/index/web-sections/` so later retrieval can point into the base Markdown instead of rereading the whole page.

## Asking Agents To Use An Archive

If an agent is started with `cwd` inside the archive workspace, the local `AGENTS.md` should carry the workflow already.

Minimal prompt:

```text
Answer this question using .:
"<YOUR QUESTION HERE>"
```

Audit-friendly prompt:

```text
Use . and follow the local AGENTS.md.
Answer:
"<YOUR QUESTION HERE>"

Report:
- the task type (`rule_lookup` or `case_application`)
- the exact hit ids used
- whether expansion was needed
- whether browser use was needed
```

When the runtime supports subagents, Ledger-generated archives now tell operators to use them for bounded work such as source discovery, one-source fetch/indexing, or narrow verification, while keeping final synthesis and persistence decisions in the main thread.

Generate and run evals:

```bash
uv run ledger eval generate-corpus . --limit 6
uv run ledger eval run .
uv run python scripts/run_archive_evals.py run .
```

Generated archives now include repo-local eval wrappers under `scripts/` plus a seeded `archive-evals/` workspace, so the archive repo stays operationally self-contained after `ledger archive scaffold`.

The eval runner reports:

- policy and grounding checks
- ranked retrieval metrics such as `hit@k`, `precision@k`, `recall@k`, `mrr@k`, and `ndcg@k`
- replay-style trajectory metrics such as completion pass rate, clean pass rate, drift rate, and median trace steps
- answer-quality, replay, and false-completion summary lanes when scenarios opt into those proof families

If an example archive has `archive-evals/thresholds.json`, `ledger eval run` fails on threshold regressions.
