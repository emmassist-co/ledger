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

### Helper templates

- `templates/domain-pack/claims.json`
- `templates/domain-pack/answer.json`
- `templates/domain-pack/decision.json`
- `templates/domain-pack/expansion-plan.json`

These files provide starter payload shapes for helper checks so future agents do not have to guess the expected JSON structure.

### Operator surface

- `skills/<domain-slug>-operator/SKILL.md`

This skill should stay thin. It points the agent at the local recipes, the coverage ledger, and the right helper posture.

### Eval posture

- `archive-evals/scenarios/*.json`
- `archive-evals/thresholds.json`
- `domain-benchmarks/thresholds.json`

These files should establish a starter proof surface, not a final benchmark.

## Design constraints

- Keep outputs local to the archive.
- Keep them editable and inspectable.
- Prefer generated structure over hand-written repetition.
- Add new outputs only when they create a clear reusable operating surface.
