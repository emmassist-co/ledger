# Verifier Toolkit

Use small deterministic verifiers as policy gates around the LLM.

## Purpose

The LLM should decide what to inspect, what to fetch next, and how to synthesize. Verifiers should decide whether the archive has met non-negotiable structural requirements.

Use verifiers to guarantee:

- policy boundaries were respected
- required source metadata exists
- decisive claims have evidence artifacts
- expansion is allowed for the current archive mode

Do not use verifiers to replace interpretation.

## Minimal Toolkit

Keep the toolkit small:

- `check_coverage`
- `check_provenance`
- `check_policy`
- `check_decision_record`
- `check_claim_support`
- `check_exact_wording`
- `rebuild_index`

## Recommended Responsibilities

### `check_coverage`

Return whether the current archive appears to have enough local material to attempt an answer.

Typical deterministic signals:

- matching registry artifacts exist
- matching extract artifacts exist
- linked canonical artifacts exist when required by mode
- candidate counts by artifact family

### `check_provenance`

Return whether answer-critical artifacts have the required source fields.

Typical deterministic signals:

- source URL present
- local source path present when required
- source hash present when required
- extract pointer or page/article anchor present

### `check_policy`

Return whether a proposed expansion or answer is allowed by archive policy.

Typical deterministic signals:

- requested action is in-bounds for agreed corpus
- `operating_mode` rules are satisfied
- `autonomy_policy` permits automatic expansion
- negative-claim restrictions are respected

### `check_claim_support`

Return whether the final answer claims have enough referenced evidence artifacts.

Typical deterministic signals:

- every answer-critical claim cites at least one extract or canonical artifact id
- claims do not cite summary-only artifacts when mode requires extract evidence
- missing-support claims are reported explicitly

### `check_decision_record`

Return whether a proposed action uses the required structured fields and allowed enum values.

Typical deterministic signals:

- required keys exist
- `action` is allowed
- `artifact_kind` is allowed
- `skip_reason` is present when required
- `skip_reason` belongs to the closed vocabulary
- `scope_status` may be `insufficient_input` when the topic is underspecified

### `check_exact_wording`

Return whether claims marked as relying on exact wording have `raw_source` or `extract` evidence.

Typical deterministic signals:

- each exact-wording claim declares `support_kind`
- `support_kind` is `raw_source` or `extract`
- summary-only support is rejected for exact-wording claims

### `rebuild_index`

Recompute the navigation layer from the artifact tree and deterministic metadata.

Do not make this a smart inference step.

## Output Contract

Each verifier should emit compact machine-readable output. JSON is preferred.

Suggested shape:

```json
{
  "ok": true,
  "check": "check_provenance",
  "mode": "balanced",
  "summary": "all required provenance fields present",
  "counts": {
    "artifacts_checked": 3,
    "missing_fields": 0
  },
  "failures": []
}
```

Suggested decision-record shape:

```json
{
  "action": "persist",
  "reason": "official source used to answer and likely reusable",
  "source_type": "official",
  "scope_status": "in_bounds",
  "artifact_kind": "canonical"
}
```

When a check fails, return actionable failures:

```json
{
  "ok": false,
  "check": "check_claim_support",
  "mode": "accuracy_first",
  "summary": "2 claims lack extract-level evidence",
  "failures": [
    {
      "claim_id": "claim-2",
      "reason": "no extract artifact linked"
    }
  ]
}
```

## Mode Expectations

- `accuracy_first`: require canonical and extract-level checks for decisive claims
- `balanced`: require provenance and policy checks, plus claim support for decisive claims
- `speed_first`: still require policy and provenance checks, but allow earlier tentative coverage outcomes

For all modes:

- block `skip_persist` without an allowed `skip_reason`
- block exact-wording claims without `raw_source` or `extract` support

Treat these distinctions as important:

- `duplicate`: reusable artifact already exists
- `insufficient_value`: candidate artifact is still not worth persisting even though it is not a literal duplicate
- `insufficient_input`: not enough topic detail to classify the next step honestly

## Anti-Patterns

- building a large verifier framework before archive behavior is proven
- using verifiers to score semantic truth
- hiding failed checks from the final retrieval report
- letting the LLM bypass verifier failures silently
