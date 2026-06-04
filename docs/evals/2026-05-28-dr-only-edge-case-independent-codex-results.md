---
title: "DR-Only Edge-Case Independent Codex Results"
type: eval_result
status: draft
date: 2026-05-28
---

# DR-Only Edge-Case Independent Codex Results

Run shape:

- runner: local `codex exec`
- session style: one cold independent session per question
- workspace: `archive-index`, using isolated temporary copies for the parallel runs
- config isolation: `--ephemeral --ignore-user-config --ignore-rules`
- source policy: `DR` only
- benchmark mode: `archive first -> expand if weak -> persist -> answer`

## Headline

- total questions: `12`
- completed answers: `12`
- scored `pass`: `12`
- scored `partial`: `0`
- scored `fail`: `0`
- `used_only_dr`: `12/12`
- runs needing a timeout retry: `2/12`

## High-Level Read

This was much stronger than the earlier archive-only diagnostics.

On this edge-case-heavy set, cold independent Codex sessions were able to:

- stay inside `DR` source discipline
- expand when local support was weak
- persist reusable article-level slices
- answer correctly on stranger legal-rule questions, not just archive-shaped tax slices

That is a materially better signal than the earlier mixed-source or archive-only tests.

## Per Question

### PT-DR-EDGE-001

- result: `pass`
- note:
  Correctly grounded telework additional-expense compensation in article 168 and persisted a reusable extract.

### PT-DR-EDGE-002

- result: `pass`
- note:
  Correctly recovered the special telework right for `cuidador informal nao principal`, including the `4 years` limit and compatibility/resource conditions.

### PT-DR-EDGE-003

- result: `pass`
- note:
  Correctly handled the oddity that `peoes` involved in traffic accidents also fall into the alcohol-test rule, with blood collection as fallback.

### PT-DR-EDGE-004

- result: `pass`
- note:
  Correctly answered the base `sinal` rule: loss of signal if the giver defaults, double if the receiver defaults.

### PT-DR-EDGE-005

- result: `pass`
- note:
  Correctly answered the parent-to-child sale rule, including consent of the other children, judicial substitution, annulability, and the one-year challenge window.

### PT-DR-EDGE-006

- result: `pass`
- note:
  Correctly ordered the maintenance-obligation edge case: siblings before uncles/aunts, and stepfather/stepmother only after that in the minor-stepchild situation.

### PT-DR-EDGE-007

- result: `pass`
- note:
  Correctly answered the companion-animal moral-damage question from an existing local DR extract and correctly skipped duplicate persistence.

### PT-DR-EDGE-008

- result: `pass`
- note:
  Correctly answered that companion animals already held at marriage are excluded from the marital community and persisted the extract for article 1733.

### PT-DR-EDGE-009

- result: `pass`
- note:
  Correctly answered the `15 years` / `20 years` usucapião rule for immovables without title-registration or possession-registration.

### PT-DR-EDGE-010

- result: `pass`
- note:
  Correctly answered the less-obvious renewal rule: if the initial fixed term is under `3 years`, renewal is for `3 years` in the ordinary case.

### PT-DR-EDGE-011

- result: `pass`
- note:
  Correctly answered that manifest material/calculation errors in administrative acts may be rectified `a todo o tempo`, while keeping the answer scoped to true rectification.

### PT-DR-EDGE-012

- result: `pass`
- note:
  Correctly answered the landlord opposition-to-renewal window of `120 days` for fixed terms between `1` and `6` years.

## Important Observations

### Good

- The independent sessions did not drift to `AT`, `gov.pt`, `IMT`, `Justiça`, or `Segurança Social`.
- The set was genuinely broader than the current archive's original center of gravity.
- Most questions triggered real DR expansion and reusable local persistence rather than shallow local reuse.

### Less Good

- These cold sessions are still expensive.
- Two questions timed out on the first attempt and needed individual reruns.
- Several runs still consumed a lot of tokens for what should become a smaller operator loop.

### Quirks

- Some outputs reported persisted artifact paths as absolute workspace paths rather than relative archive paths.
- Some answers cited both a consolidated `DR` URL and a `files.diariodarepublica.pt` PDF URL. That is still within the intended `DR` source family.
- Question `PT-DR-EDGE-005` also cited the `DR` Lexionário. That is acceptable for this benchmark because it is still a `DR` surface, but the decisive rule stayed anchored in the statutory article.

## What This Means

The agent is much more capable in `DR-only expand mode` than the earlier archive-only tests suggested.

The real remaining issue is no longer "can it answer weird DR-only questions at all?" It can.

The remaining issues are:

- cost and latency of the cold operator loop
- harder enforcement and reporting around exact source-family choices
- cleaner persistence bookkeeping and path reporting
- turning this ad hoc run shape into a repeatable benchmark harness

## Artifacts

- benchmark set: `docs/evals/2026-05-28-dr-only-edge-case-portuguese-legal-benchmark.md`
- raw outputs:
  - `docs/evals/dr-edge-cold-runs`
  - `docs/evals/dr-edge-independent-runs`
