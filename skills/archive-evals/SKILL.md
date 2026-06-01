---
name: archive-evals
description: Use when validating whether an archive built with archive-index-builder can answer grounded questions correctly, stay within archive policy, and generate or run small deterministic eval suites.
---

# Archive Evals

Use this as a companion to `archive-index-builder`, not as a replacement for it.

## Rules

- Evaluate the real archive-answering path, not a polished final answer in isolation.
- For product scoring, default to `archive first -> expand if weak -> persist -> answer -> rerun later`.
- Treat `archive-only` runs as diagnostic coverage checks, not the main benchmark lane.
- Keep deterministic checks primary and LLM judging secondary.
- Start with a small eval set before expanding.
- Prefer floor-raising over benchmark-maxxing: protect critical-path failures before chasing broad synthetic coverage.
- Prefer corpus-derived scenarios plus a few user-seeded must-answer questions.
- Treat user-seeded must-answer questions as golden cases.
- When a real archive failure is reproduced, add it as a production-derived regression before adding more speculative coverage.
- Separate `retrieval`, `grounding`, and `boundary` failures.
- Separate answer-posture failures from retrieval failures when scenarios declare `answer_expectations`.
- Score trajectory separately from completion when the runtime is replay-based or partially deterministic.
- Reuse the archive-side verifier toolkit when possible.
- For archives with `recipes/source-discovery.yaml`, include currentness/freshness scenarios that validate listing sync state and latest local-ingest state.
- Do not build a benchmark platform when a small scenario set will do.
- Prune or review stale passing cases instead of letting the suite grow forever.

## Workflow

1. Inspect the archive workspace, policy, and verifier policy.
2. Determine whether the archive purpose is already clear from the corpus and docs.
3. If not clear enough, ask the user for a few must-answer questions.
4. Scaffold an eval workspace if one does not exist.
5. Generate a small corpus-derived scenario set.
6. Add user-seeded scenarios when needed.
7. Mark the few must-not-break cases as `golden` and `critical_path` in `case_metadata`.
8. When a real failure produced this case, record that in `case_metadata.origin` and keep the failure class small and explicit.
9. Run deterministic eval checks first.
10. Report results grouped by `retrieval`, `grounding`, and `boundary`, plus separate golden-case and critical-path health.
11. When scenarios include `answer_expectations`, score answer posture separately from retrieval.
12. Recommend the smallest next hardening step and identify stale cases worth pruning or reviewing.

Read [references/scenario-schema.md](references/scenario-schema.md) before writing scenarios.
Read [references/buckets-and-reporting.md](references/buckets-and-reporting.md) before scoring or reporting results.

## Scenario Sources

Use two sources:

- `corpus_derived`: inferred from prominent artifacts already in the archive
- `user_seeded`: must-answer questions supplied by the user or inferred from archive purpose docs

Start with 3 to 5 total scenarios unless the user asks for broader coverage.

Default mix:

- 2 to 3 `golden` cases covering must-not-break archive behavior
- 1 to 2 `coverage` cases derived from the corpus
- 0 to 1 fresh `production_derived` regression when a real failure exists

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
2. run the real archive-answering flow if available, with expansion enabled unless the scenario explicitly says otherwise
3. otherwise run the deterministic archive checks and artifact-presence checks
4. record the result as `pass`, `pass_with_drift`, or `fail`

When a full interactive agent runtime is not available, prefer a replay-style trajectory layer:

- record the archive query step
- record which deterministic verifiers ran
- record whether a verifier pass or an expected safety block happened
- score route quality separately from completion

When no generic answer runtime exists yet, do not fake it. Report that the eval currently verifies archive readiness and evidence support rather than full answer execution.

When `answer_expectations` are present, use them to score whether the archive is set up to answer in the right mode and with the right contract, even if there is no fully generic answer runtime yet.

For benchmark suites, report first-run expand-mode outcomes separately from second-run local reuse. Do not collapse those into a single score.

Use `case_metadata` to keep the suite honest:

- `tier`: `golden`, `coverage`, or `regression`
- `criticality`: `critical`, `high`, `medium`, or `low`
- `critical_path`: `true` when this is a ship-blocking path
- `origin`: `user_seeded`, `corpus_derived`, or `production_derived`
- `failure_class`: short pattern label such as `exact_wording`, `missing_facts`, or `weak_local_support`
- `stale_after_days`: review/prune threshold for passing cases
- `added_at`, `last_failed_at`, `last_reviewed_at`: optional dates for hygiene reporting

## Output

Produce:

- an eval manifest
- scenario files
- raw JSON reports
- threshold files when the archive has committed benchmark fixtures
- a short summary grouped by bucket
- a golden/critical-path health summary
- a prune-review list for stale passing cases when metadata is available

## Minimal Tooling

Use the bundled scripts:

- `scripts/scaffold_archive_evals.py`
- `scripts/run_archive_evals.py`

Keep custom code small. The scripts should only do deterministic setup, generation, and checking.

When examples are committed into the repo, prefer adding:

- `archive-evals/thresholds.json` in each example
- a generated repo-level benchmark summary
