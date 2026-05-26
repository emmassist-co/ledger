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

- `source_kind`
- `notes`

## Example

```json
{
  "id": "retrieval-core-policy",
  "bucket": "retrieval",
  "source_kind": "corpus_derived",
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
  ]
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
