# Expansion Recipes

The domain pack should keep archive growth editable and local to the archive.

Use these files:

- `recipes/source-acquisition.yaml`
  - allowed source families
  - question-shape source-family policy
  - preferred source family by shape
  - bounded first-pass and refinement budgets
  - fallback policy
  - raw-source capture defaults
  - skip-persist reasons
- `recipes/extract-units.yaml`
  - what retrieval unit each source family uses
  - whether the unit should materialize as `extract` or `derived_summary`
  - whether exact wording prefers that unit
- `recipes/persistence-rules.yaml`
  - what is durable enough to persist
  - what should stay ephemeral
  - exact-wording persistence expectations
- `domain/coverage-ledger.yaml`
  - covered topics
  - partial topics
  - stale topics
  - source families already seen
- `domain/expansion-report-template.md`
  - the report shape future agents should leave after significant archive growth

These files are designed to be changed by the operator for a specific domain.

For bounded canonical expansion, the pack should make these decisions explicit:

- the question shapes the archive recognizes
- which source families are allowed for each shape
- which source family is preferred first
- whether a second search stage is allowed
- how many queries belong to each search stage
- whether the archive may widen beyond the canonical family at all

Ledger core should validate the shape and the allowed transitions, but the domain pack should keep the actual domain policy editable.

Adjacent answer-discipline files:

- `recipes/support-hierarchy.yaml`
  - what support level decisive claims require
  - whether each decisive claim must be labeled
- `recipes/confirmation-thresholds.yaml`
  - what counts as a merely plausible case application
  - what counts as confirmed from provided facts
  - which phrases are too strong when blocking facts remain unresolved
