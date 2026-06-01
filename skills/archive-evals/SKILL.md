---
name: archive-evals
description: Use when validating whether an archive built with archive-index-builder can answer grounded questions correctly, stay within archive policy, and generate or run small deterministic eval suites.
---

# Archive Evals

Use this as a companion to `archive-index-builder`, not as a replacement for it.

## Rules

- Evaluate the real archive-answering path, not a polished final answer in isolation.
- Keep deterministic checks primary and LLM judging secondary.
- Start with a small eval set before expanding.
- Prefer corpus-derived scenarios plus a few user-seeded must-answer questions.
- Separate `retrieval`, `grounding`, and `boundary` failures.
- Separate answer-posture failures from retrieval failures when scenarios declare `answer_expectations`.
- Score trajectory separately from completion when the runtime is replay-based or partially deterministic.
- Reuse the archive-side verifier toolkit when possible.
- For archives with `recipes/source-discovery.yaml`, include currentness/freshness scenarios that validate listing sync state and latest local-ingest state.
- Do not build a benchmark platform when a small scenario set will do.

## Workflow

1. Inspect the archive workspace, policy, and verifier policy.
2. Determine whether the archive purpose is already clear from the corpus and docs.
3. If not clear enough, ask the user for a few must-answer questions.
4. Scaffold an eval workspace if one does not exist.
5. Generate a small corpus-derived scenario set.
6. Add user-seeded scenarios when needed.
7. Run deterministic eval checks first.
8. Report results grouped by `retrieval`, `grounding`, and `boundary`, plus a separate trajectory summary.
9. When scenarios include `answer_expectations`, score answer posture separately from retrieval.
10. Recommend the smallest next hardening step.

Read [references/scenario-schema.md](references/scenario-schema.md) before writing scenarios.
Read [references/buckets-and-reporting.md](references/buckets-and-reporting.md) before scoring or reporting results.

## Scenario Sources

Use two sources:

- `corpus_derived`: inferred from prominent artifacts already in the archive
- `user_seeded`: must-answer questions supplied by the user or inferred from archive purpose docs

Start with 3 to 5 total scenarios unless the user asks for broader coverage.

## Deterministic Checks

Prefer these first:

- `check_coverage`
- `check_provenance`
- `check_policy`
- `check_claim_support`
- `check_exact_wording`
- `check_decision_record`
- `check_coverage_state`
- `check_auto_expand_decision`

If the archive exposes more specific deterministic checks, use them.

## Runtime Contract

For each scenario:

1. identify the expected artifact family and constraints
2. run the real archive-answering flow if available
3. otherwise run the deterministic archive checks and artifact-presence checks
4. record the result as `pass`, `pass_with_drift`, or `fail`

When a full interactive agent runtime is not available, prefer a replay-style trajectory layer:

- record the archive query step
- record which deterministic verifiers ran
- record whether a verifier pass or an expected safety block happened
- score route quality separately from completion

When no generic answer runtime exists yet, do not fake it. Report that the eval currently verifies archive readiness and evidence support rather than full answer execution.

When `answer_expectations` are present, use them to score whether the archive is set up to answer in the right mode and with the right contract, even if there is no fully generic answer runtime yet.

## Output

Produce:

- an eval manifest
- scenario files
- raw JSON reports
- threshold files when the archive has committed benchmark fixtures
- a short summary grouped by bucket

## Minimal Tooling

Use the bundled scripts:

- `scripts/scaffold_archive_evals.py`
- `scripts/run_archive_evals.py`

Keep custom code small. The scripts should only do deterministic setup, generation, and checking.

When examples are committed into the repo, prefer adding:

- `archive-evals/thresholds.json` in each example
- a generated repo-level benchmark summary
