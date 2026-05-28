# Scenario Schema

Keep scenarios small, explicit, and machine-checkable.

## Required Fields

- `id`
- `bucket`
- `prompt`
- `expected_artifacts`
- `expected_constraints`
- `verifier_checks`

## Optional Fields

- `query`
- `retrieval_k`
- `relevance_judgments`
- `source_kind`
- `notes`
- `expected_verifier_outcomes`
- `trajectory_expectations`
- `answer_expectations`

## Example

```json
{
  "id": "retrieval-core-policy",
  "bucket": "retrieval",
  "source_kind": "corpus_derived",
  "query": "core policy source",
  "prompt": "What is the canonical source behind the archive's core policy topic?",
  "expected_artifacts": [
    "reg-core-policy",
    "res-core-policy-crosswalk"
  ],
  "expected_constraints": {
    "require_any_artifact_match": true,
    "require_extract_evidence": false,
    "policy_action": "answer"
  },
  "verifier_checks": [
    "check_coverage",
    "check_policy"
  ],
  "relevance_judgments": {
    "reg-core-policy": 2,
    "res-core-policy-crosswalk": 1
  },
  "trajectory_expectations": {
    "required_events": [
      "archive.query",
      "archive.retrieve.hit",
      "verifier.check_coverage.pass"
    ],
    "max_first_relevant_rank": 2,
    "preferred_artifact_types": [
      "registry"
    ]
  },
  "answer_expectations": {
    "response_mode": "direct_answer",
    "expected_decision_action": "answer",
    "required_answer_sections": [
      "rule_found",
      "evidence_type"
    ],
    "must_declare_missing_facts": false,
    "must_declare_verified_at": false
  }
}
```

## Buckets

- `retrieval`
- `grounding`
- `boundary`

## Constraints

Prefer explicit booleans or short strings:

- `require_any_artifact_match`
- `require_extract_evidence`
- `policy_action`
- `autonomy_policy`

Do not encode a hidden gold answer in the scenario prompt.

## Retrieval Metrics

The eval runner may compute:

- `hit@k`
- `precision@k`
- `recall@k`
- `mrr@k`
- `ndcg@k`

Use `query` for the ranked retrieval input.
Use `relevance_judgments` when you want graded relevance for `ndcg`; otherwise `expected_artifacts` is treated as a binary relevant set.

## Trajectory Expectations

Use `trajectory_expectations` for replay-style route checks:

- `required_events`
- `forbidden_events`
- `max_first_relevant_rank`
- `preferred_artifact_types`
- `max_verifier_calls`
- `max_trace_steps`
- `decision_record`
- `exact_wording_claim`

Use `expected_verifier_outcomes` when a boundary scenario should succeed because a verifier blocked unsafe behavior, for example:

- `check_exact_wording: false`
- `check_coverage_state: false`
- `check_auto_expand_decision: true`

## Answer Expectations

Use `answer_expectations` when you want the eval to score answer posture, not only retrieval and verifier replay.

Supported fields:

- `response_mode`: `direct_answer`, `answer_with_missing_facts`, `expand_then_answer`, or `safety_block`
- `expected_decision_action`
- `minimum_quality_status`
- `required_answer_sections`
- `must_declare_missing_facts`
- `must_declare_verified_at`
- `replay_expected_response_mode`
- `false_completion_expected_response_mode`

These fields are intentionally lighter than a full gold answer. They let the eval ask whether the archive is set up to answer the question in the right mode with the right contract.

Use `expand_then_answer` when a scenario should detect a known support gap or partial topic and choose expansion before treating the answer as target-quality complete.

Use `replay_expected_response_mode` for scenarios that stand in for a later run after persistence and should now land as a stronger local hit.

Use `false_completion_expected_response_mode` for scenarios that should prove the archive blocked a premature direct answer and took the safer route instead.
