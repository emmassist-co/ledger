# Parliament

Artifact-first workflow for Portuguese parliamentary transcript PDFs.

This repository tracks the reusable workflow, skills, prompts, code, and tests.
The live `archive-index/` workspace is intentionally excluded from Git and treated as local generated/runtime state.

## Usage

```bash
uv run parliament process /path/to/DAR-I-087.pdf
```

## Environment

Add your real OpenRouter key in [.env](/Users/alexandre/dev/parliament/.env):

```bash
OPENROUTER_API_KEY=your-openrouter-api-key-here
```

There is also a starter template in [.env.example](/Users/alexandre/dev/parliament/.env.example).

For local non-network testing, set:

```bash
PARLIAMENT_FAKE_LLM_OUTPUT="Texto gerado"
```

## Model Configuration

Per-stage model selection lives in:

- [config/models.local.yaml](/Users/alexandre/dev/parliament/config/models.local.yaml) for your active local config
- [config/models.example.yaml](/Users/alexandre/dev/parliament/config/models.example.yaml) as the template

The current configurable spending surfaces are:

- `models.section_note`
- `models.claims`
- `models.index`
- `models.level_1`
- `models.level_2`
- `models.level_3`

Use the local config file directly, or edit it if you want different models by stage.

```bash
uv run parliament process /path/to/DAR-I-087.pdf --config config/models.local.yaml
```
