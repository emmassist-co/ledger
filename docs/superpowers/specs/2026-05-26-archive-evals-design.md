# Archive Evals Design

## Goal

Create a companion skill, `archive-evals`, that validates whether an archive built with `archive-index-builder` can answer grounded questions correctly and stay within archive policy.

This is a separate skill, not embedded into the builder. The builder should link to it and share a small contract with it.

## Why This Exists

The archive builder can create and grow evidence-preserving archives incrementally, but growth alone does not show that the archive:

- retrieves the right artifacts,
- grounds decisive claims in the right evidence,
- stays inside expansion and confidence policy,
- avoids unsupported negative claims.

The missing capability is a repeatable eval layer that exercises the real archive-answering flow and checks it with deterministic gates.

## Scope

### In scope

- Define a separate `archive-evals` skill
- Make it inspect an existing archive workspace and policy
- Generate eval scenarios from both corpus content and user-seeded questions
- Run deterministic checks over real archive-answering runs
- Report results in retrieval, grounding, and boundary buckets

### Out of scope

- Embedding eval logic directly into `archive-index-builder`
- Building a large benchmark platform
- Replacing deterministic checks with LLM judging
- Solving semantic truth entirely through code

## Core Design

### Skill boundary

`archive-index-builder` remains responsible for:

- intake
- acquisition
- extraction
- indexing
- verifier-aware archive growth

`archive-evals` is responsible for:

- generating realistic archive questions
- running the real answering flow
- checking whether the archive answers correctly and safely

The builder should reference the eval skill in its docs and scaffold, but not embed the workflow itself.

### Eval inputs

The eval skill should use:

- the archive workspace
- the archive policy/config
- the archive verifier policy
- existing artifact families
- optional user-seeded “must-answer” questions

### Eval outputs

The eval skill should produce:

- an eval manifest
- a scenario set
- raw run artifacts
- deterministic verifier outputs
- a final report grouped by eval bucket

## Eval Buckets

### 1. Retrieval

Purpose:

- test whether the archive finds the correct registry, extract, and derived artifacts for a question

Checks:

- expected artifacts appear in candidate results
- required extract or canonical artifacts are reachable
- candidate set is not empty when coverage should exist

### 2. Grounding

Purpose:

- test whether the final answer’s decisive claims are supported by the right extract or canonical evidence

Checks:

- answer-critical claims cite evidence artifacts
- the cited artifacts match the expected family and scope
- `accuracy_first` archives require stronger extract/canonical support

### 3. Boundary

Purpose:

- test whether the archive stayed inside policy while answering

Checks:

- no unsupported negative claims
- no unjustified expansion
- no policy/mode violations
- no claim of confidence beyond what the archive mode allows

## Scenario Sources

The skill should generate scenarios from two sources.

### Corpus-derived scenarios

Generate a small set from the archive’s own content:

- canonical acts or anchors
- prominent extract artifacts
- cross-corpus links
- common reference artifacts

This checks whether the archive can answer questions implied by what it already contains.

### User-seeded scenarios

Ask for a small set of “must-answer” questions when needed, especially when the archive has a narrow business purpose.

These should represent:

- core use cases
- high-value queries
- edge cases the user cares about

## Scenario Shape

Keep the scenario schema small and machine-checkable.

Required fields:

- `id`
- `bucket`
- `prompt`
- `expected_artifacts`
- `expected_constraints`
- `verifier_checks`

Optional fields:

- `source_kind` such as `corpus_derived` or `user_seeded`
- `notes`

## Runtime Contract

For each scenario:

1. run the real archive-answering flow
2. collect produced answer and trace artifacts
3. run deterministic verifier checks first
4. score result as:
   - `pass`
   - `pass_with_drift`
   - `fail`

Deterministic checks should dominate completion scoring. LLM judging, if used at all, is sidecar-only.

## Verifier Use

The eval skill should reuse the archive-side verifier toolkit where possible.

Minimum expected checks:

- `check_coverage`
- `check_provenance`
- `check_policy`
- `check_claim_support`

The eval skill may add small scenario-family checks, but should not grow a large framework unless repeated use proves the need.

## Reporting

The final report should group outcomes by:

- retrieval
- grounding
- boundary

For each scenario it should show:

- status
- key failures
- verifier results
- whether the failure is coverage, grounding, or policy related

At the archive level it should show:

- bucket pass rates
- common failure modes
- recommended next hardening steps

## Recommended Defaults

Start small:

- 3 to 5 corpus-derived scenarios
- 3 to 5 user-seeded scenarios
- deterministic checks first
- no heavy orchestration

The goal is not benchmark theater. The goal is to tell whether the archive is actually usable and where it breaks.
