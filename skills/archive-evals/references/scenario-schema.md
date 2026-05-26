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
  "id": "retrieval-lei-13-2023",
  "bucket": "retrieval",
  "source_kind": "corpus_derived",
  "prompt": "What is the canonical law behind Agenda do Trabalho Digno?",
  "expected_artifacts": [
    "reg-dr-lei-13-2023",
    "res-agenda-do-trabalho-digno-dar-dr"
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
