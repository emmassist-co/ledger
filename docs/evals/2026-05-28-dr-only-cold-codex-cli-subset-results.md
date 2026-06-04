---
title: "DR-Only Cold Codex CLI Subset Results"
type: eval_result
status: draft
date: 2026-05-28
---

# DR-Only Cold Codex CLI Subset Results

Run shape:

- runner: local `codex exec`
- workdir: `archive-index`
- config isolation: `--ephemeral --ignore-user-config --ignore-rules`
- web access: disabled
- archive mode: local files only
- conversation context: none from this thread

This was a **diagnostic cold/local-only run**, not the recommended benchmark mode.
For this benchmark family, the primary score should come from `DR-only expand mode`.

## Important note

The CLI run did not emit a clean final JSON payload before being stopped, so this result is scored from the completed command trace rather than from the model's final formatted answer.

That is still useful here because the trace clearly shows:

- which local artifacts the cold agent found and read
- which topics it considered directly supported
- which topics it could not ground from promoted local artifacts
- where it drifted toward the wrong local source family for a DR-only benchmark

## Subset

Representative `4`-question subset:

- `PT-DR-001`
- `PT-DR-004`
- `PT-DR-010`
- `PT-DR-013`

## Headline

- total questions: `4`
- `pass/direct`: `1`
- `partial`: `1`
- `insufficient`: `2`

## Per Question

### PT-DR-001

- result: `pass`
- local support posture: `direct_local_support`
- artifacts:
  - `ext-cirs-art10-hpp-reinvestment-current`
  - `note-cirs-hpp-reinvestment`
- read:
  The cold agent immediately found the HPP reinvestment extract and note. The local archive has enough to answer the legal conditions coherently.
- caveat:
  The support is local and strong, but the promoted extract is currently an AT capture rather than a DR extract. That is good enough for a cold-archive test, but not ideal for a strict DR-only benchmark.

### PT-DR-004

- result: `partial`
- local support posture: `partial_local_support`
- artifacts:
  - `art-ce-pontos`
  - `domain/coverage-ledger.yaml`
- read:
  The cold agent found the current article-block summary for article 148 and the coverage ledger. It had enough to recover the main 2/4-point ordinary rule and the existence of progressive consequences.
- caveat:
  This slice is explicitly marked `below_target` in `coverage-ledger.yaml` because the archive only has an `article_block`, not a dedicated extract. So this is usable support, but not yet top-tier DR support for a strict legal benchmark.

### PT-DR-010

- result: `insufficient`
- local support posture: `insufficient_local_support`
- read:
  The cold agent searched the local archive for `periodo experimental`, `contrato de trabalho`, `90 dias`, and related terms, but only found parliamentary debate/transcript material and no promoted Código do Trabalho artifact.
- conclusion:
  Correct archive behavior for this cold run is to abstain. The local archive does not yet materially cover this rule.

### PT-DR-013

- result: `insufficient`
- local support posture: `insufficient_local_support`
- read:
  The cold agent searched for `arrendatario`, `denunciar`, `prazo certo`, `120 dias`, and `60 dias`, but again only found scattered parliamentary or unrelated material, not a promoted Código Civil / arrendamento slice.
- conclusion:
  Correct archive behavior for this cold run is to abstain. The local archive does not yet materially cover this rule.

## Main Finding

The useful signal is not only coverage.

The bigger issue is source-family drift:

- even in a DR-only benchmark, the cold agent naturally read local AT extracts and a local `gov.pt`-anchored housing note when those were present
- that means the current archive/operator surface does **not yet enforce DR-only source selection strongly enough**

So there are really two results here:

1. archive coverage result:
   - tax and road-traffic slices have some usable local support
   - labor and civil-code slices are not yet materially present

2. benchmark-discipline result:
   - the cold agent still needs a harder guardrail to refuse non-DR local artifacts when the benchmark says `DR-only`

3. benchmark-mode result:
   - this run shape is useful for diagnostics, but it should not be treated as the primary product score
   - the next real score should come from `archive first -> DR-only expand -> persist -> answer -> rerun`

## What this means

For a DR-only benchmark, we should not just ask different questions.

We also need a stronger execution mode such as:

- `allowed_source_systems = ["diariodarepublica.pt"]`
- fail or downgrade when the answer leans on `AT`, `gov.pt`, `justica.gov.pt`, `IMT`, or other local official sources
- separate `DR-only legal mode` from `mixed official-sources mode`

Without that, the archive can still look "good" by answering from the wrong official layer.
