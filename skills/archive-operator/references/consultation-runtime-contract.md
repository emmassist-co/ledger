# Consultation Runtime Contract

This contract defines the reduced deterministic consultation slice used by generated archive-local wrappers.

## Purpose

Given:

- an archive root
- a natural-language question
- optional user facts

the consultation runtime produces one machine-readable audit artifact that tells the operator whether the next step is:

- `decisive_answer`
- `expand`
- `ask_user`

The runtime does not synthesize the final legal or domain answer. It standardizes the gating decision before that answer.

## Question Shapes

- `rule_lookup`: general rule or source lookup with no user-specific fact pattern required
- `case_application`: a question that depends on user-specific facts
- `archive_audit`: a question about whether the archive or prior operator behavior was sufficient

If the caller does not force a question shape, the runtime classifies it deterministically.

## Audit Payload Fields

The runtime audit payload must include:

- `schema_version`
- `consultation_runtime_version`
- `generated_at`
- `archive_root`
- `question`
- `question_shape`
- `user_facts`
- `missing_user_facts`
- `support_state`
- `currentness_sensitive`
- `currentness_state`
- `candidate_artifacts`
- `coverage_state`
- `archive_state_summary`
- `outcome`
- `outcome_reasons`
- `recommended_next_step`

## Outcome Semantics

- `decisive_answer`: the operator may answer from local archive support and current state
- `expand`: the archive needs more source support or freshness support before a decisive answer
- `ask_user`: required user facts are missing for a case application

## Precedence Model

Apply gates in this order:

1. Missing required user facts block case application and yield `ask_user`.
2. No local support yields `expand`.
3. A failing coverage-state gate yields `expand`.
4. A currentness-sensitive question without usable freshness state yields `expand`.
5. Otherwise yield `decisive_answer`.

This reduced slice intentionally stops here. Stronger support hierarchy checks, confirmation thresholds, and mutation helpers remain outside this first implementation.
