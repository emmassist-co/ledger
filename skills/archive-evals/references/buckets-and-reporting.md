# Buckets And Reporting

Use three eval buckets.

Default benchmark posture:

- first-run score: `archive first -> expand if weak -> persist -> answer`
- second-run score: local reuse after persistence
- `archive-only` score: diagnostic only

## Retrieval

Ask:

- did the archive surface the expected artifact family?
- are the expected artifact ids present?
- is there enough local coverage to attempt an answer?

## Grounding

Ask:

- do decisive claims have evidence artifacts?
- do those artifacts match the expected scope?
- does the archive mode require extract-level evidence here?

## Boundary

Ask:

- did the flow stay inside archive policy?
- did it avoid unsupported negative claims?
- did it avoid unjustified expansion?

## Status Levels

- `pass`: deterministic checks succeeded
- `pass_with_drift`: core checks passed, but there are quality or coverage warnings
- `fail`: deterministic checks failed

## Report Shape

At minimum:

- scenario id
- bucket
- status
- answer evaluation
- retrieval metrics
- trajectory events and drift reasons
- verifier results
- failures
- recommended next step

At archive level:

- pass counts by bucket
- average retrieval metrics overall
- average retrieval metrics by bucket
- suite health metrics:
  - golden-case count and pass rate
  - critical-path count and pass rate
  - counts by `origin`, `tier`, and `criticality`
  - top failing golden or critical-path scenarios
- trajectory metrics:
  - completion pass rate
  - clean pass rate
  - drift rate
  - median trace steps
  - median verifier calls
- answer quality metrics:
  - checked scenario count
  - pass rate on checked scenarios
  - response-mode counts
  - common answer-contract failures
- replay metrics:
  - replay scenario count
  - second-run local-hit rate
  - common replay failures
- expand-mode metrics:
  - expand scenario count
  - expand success rate
  - answer pass rate after expand
  - persistence success rate
  - wrong source rate
  - common expansion failures
- false-completion metrics:
  - guarded-scenario count
  - guard success rate
  - false completion rate
  - common guard failures
- prune-review metrics:
  - stale passing-case count
  - candidate ids with age and threshold
- common failure modes
- recommended hardening steps

Order the summary for floor-raising:

1. failing golden or critical-path cases
2. expansion failures that prevented correct first-run closure
3. common failure classes worth turning into targeted regressions
4. stale cases that may no longer justify their maintenance cost
5. broad retrieval diagnostics
