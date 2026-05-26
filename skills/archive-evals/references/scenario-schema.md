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
