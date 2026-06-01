# Integration Points

## Domain pack inputs

Exploration results should feed:

- `recipes/source-families.yaml`
- `recipes/source-playbooks.yaml`
- `recipes/source-acquisition.yaml`
- `recipes/freshness-rules.yaml`

Suggested fields to derive:

- `seed_urls`
- `source_shape`
- `retrieval_unit`
- `recommended_acquisition_mode`
- `browser_escalation_allowed`
- `refresh_surface`
- `canonical_pointer_pattern`

## Archive scaffold inputs

Exploration results should inform which generic helpers the archive scaffold expects:

- registry sync helper
- document ingest helper
- fetch wrapper
- probe helper

The archive scaffold should stay generic. The source explorer decides what generic helper is needed, not how the source family is hardcoded into Ledger core.

## Operator-skill implications

The generated operator skill should learn:

- which surface to try first
- what counts as noise
- when browser escalation is allowed
- what to persist after a successful fetch
