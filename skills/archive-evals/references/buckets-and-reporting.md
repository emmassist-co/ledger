# Buckets And Reporting

Use three eval buckets.

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
- retrieval metrics
- trajectory events and drift reasons
- verifier results
- failures
- recommended next step

At archive level:

- pass counts by bucket
- average retrieval metrics overall
- average retrieval metrics by bucket
- trajectory metrics:
  - completion pass rate
  - clean pass rate
  - drift rate
  - median trace steps
  - median verifier calls
- common failure modes
- recommended hardening steps
