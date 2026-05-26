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
- `src/ledger/archive_index/`: archive artifact, navigation, and DR helper code

This repo is archive-first. It includes corpus-specific examples and source-processing helpers, but the reusable center is the archive/index workflow.

## Environment

Add your real OpenRouter key in [.env](.env):

```bash
OPENROUTER_API_KEY=your-openrouter-api-key-here
```

There is also a starter template in [.env.example](.env.example).

For local non-network testing, set:

```bash
LEDGER_FAKE_LLM_OUTPUT="Texto gerado"
```

## Model Configuration

Per-stage model selection lives in:

- `config/models.local.yaml` for your active local config
- `config/models.example.yaml` as the template

The current configurable spending surfaces are:

- `models.section_note`
- `models.claims`
- `models.index`
- `models.level_1`
- `models.level_2`
- `models.level_3`

Use the local config file directly, or edit it if you want different models by stage.

Example corpus-processing command:

```bash
uv run ledger process /path/to/source.pdf --config config/models.local.yaml
```
