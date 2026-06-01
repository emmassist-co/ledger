# Generated Pack Outputs

The scaffolded pack should produce a small set of local artifacts that another agent can operate directly.

## Required output groups

### Profile and recipes

- `recipes/domain-profile.yaml`
- `recipes/source-families.yaml`
- `recipes/source-playbooks.yaml`
- `recipes/source-acquisition.yaml`
- `recipes/extract-units.yaml`
- `recipes/persistence-rules.yaml`
- `recipes/fact-intake.yaml`
- `recipes/freshness-rules.yaml`
- `recipes/currentness-rules.yaml`
- `recipes/exception-patterns.yaml`
- `recipes/answer-contract.yaml`
- `recipes/support-hierarchy.yaml`
- `recipes/confirmation-thresholds.yaml`

These files hold the machine-usable part of the contract.

### Domain state and operating notes

- `domain/DOMAIN.md`
- `domain/OPERATIONS.md`
- `domain/ENRICHMENT_PROTOCOL.md`
- `domain/coverage-ledger.yaml`
- `domain/expansion-report-template.md`

These files tell future agents what the domain is, what coverage state exists, and how to record growth.

`domain/coverage-ledger.yaml` is the standardized cross-index memory surface. At minimum it should carry:

- known `support_gaps`
- provisional weak-slice memory for likely below-target support
- `partial_topics`
- `stale_topics`

Generated notes should explain how each state is created, confirmed, cleared, or superseded.

### Helper templates

- `templates/domain-pack/claims.json`
- `templates/domain-pack/answer.json`
- `templates/domain-pack/currentness.json`
- `templates/domain-pack/decision.json`
- `templates/domain-pack/expansion-plan.json`

These files provide starter payload shapes for helper checks so future agents do not have to guess the expected JSON structure.

### Operator surface

- `skills/<domain-slug>-operator/SKILL.md`

This skill should stay thin. It points the agent at the local recipes, the coverage ledger, and the right helper posture.

It should also point the agent at the shared judgment points every generated archive exposes:

- coverage-state checks
- support-hierarchy checks
- currentness checks when the archive needs current-state safety
- pre-answer weakness checks
- auto-expand policy checks
- confirmation-boundary checks

### Eval posture

- `archive-evals/scenarios/*.json`
- `archive-evals/thresholds.json`
- `domain-benchmarks/thresholds.json`

These files should establish a starter proof surface, not a final benchmark.

The starter proof surface should be shaped around reusable behavior families:

- direct-answer local support
- expand-then-answer
- ask-user boundary behavior
- false-completion or missing-exception behavior
- replay-style closure after persistence

## Design constraints

- Keep outputs local to the archive.
- Keep them editable and inspectable.
- Prefer generated structure over hand-written repetition.
- Add new outputs only when they create a clear reusable operating surface.
