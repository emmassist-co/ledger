---
date: 2026-05-28
topic: bounded-canonical-expansion
title: "Bounded Canonical Expansion"
---

# Bounded Canonical Expansion

## Summary

Add a reusable `bounded_canonical_expansion` layer to Ledger so archive operators expand through the right canonical source families, issue tighter source-bounded queries, reject wrong-source drift, and stop safely after a small refinement budget instead of wandering through weak or irrelevant searches.

---

## Problem Frame

Ledger's product bet depends on question-driven archive growth from canonical sources, not on broad web search or hand-built parser logic. That means expansion quality is now a product surface, not just an implementation detail.

The current failure is twofold. First, the agent can expand on the wrong source family even when the question shape should have constrained it more tightly. Second, even when it chooses the right source family, it can still waste effort on poor or repetitive queries before finding the right page, or before giving up. Those failures hurt reliability, make answers harder to trust, and weaken the claim that Ledger grows archives in a bounded, auditable way.

The missing layer is not "how to search DR" or "how to search one website." It is a reusable expansion discipline that maps question shape to allowed canonical source families, gives the operator a bounded search plan, and makes both success and bounded failure inspectable.

---

## Key Decisions

- **KD1. This is a reusable meta layer, not a DR-specific fix.** The motivating example is `diariodarepublica.pt`, but the product surface must generalize to any canonical source system the pack defines.
- **KD2. Stable search discipline lives in the pack.** The first version should store allowed source families, search templates, and persistence expectations primarily in the domain pack rather than in ad hoc operator memory.
- **KD3. Wrong-source prevention comes first.** The first optimization target is reducing wrong-source drift, even if that means some bounded failures or some remaining inefficiency inside the correct source family.
- **KD4. Query refinement must stay bounded.** If the first canonical queries are weak, the operator may do a small second-stage refinement within the same allowed source family, but should not broaden into generic official-web exploration by default.
- **KD5. Proof must be operational.** The first version should prove full operator behavior on real benchmarks: right source family, better query discipline, bounded stopping, and improved first-run expand success.

---

## Requirements

- R1. Ledger must support a reusable `bounded_canonical_expansion` contract that applies across different canonical source systems.
- R2. The contract must map question shape to allowed source families before open-ended expansion occurs.
- R3. The contract must distinguish `allowed` source families from `preferred` source families.
- R4. If a source family is not allowed for the current question shape, the operator must not use it for expansion.

**Question-shape and source policy**

- R5. The first version must support explicit question-shape categories that are strong enough to drive expansion policy, including at least rule-like lookup versus procedure-like lookup distinctions.
- R6. The pack must define source-family policy at the level of question shape, not only at the whole-archive level.
- R7. The operator must determine the current question shape before selecting a search plan.

**Search planning**

- R8. The pack must be able to define reusable canonical search guidance for each relevant source family and question shape.
- R9. The operator must produce a bounded search plan before expansion, including the target source family and a small query budget.
- R10. The first version must improve query discipline on the correct canonical source family, not only block wrong-source expansion.
- R11. If the first canonical queries are weak, the operator may perform one bounded second-stage refinement within the same allowed source family.
- R12. The first version must not broaden from a canonical source family to general official-source exploration unless the pack explicitly permits that fallback.

**Source acceptance and stopping**

- R13. Ledger must apply a source acceptance check before treating a found page as valid support for expansion or persistence.
- R14. The source acceptance check must reject pages that fall outside the allowed source-family policy for the current question shape.
- R15. The operator must stop boundedly after the configured search and refinement budget instead of continuing with open-ended search behavior.
- R16. When bounded search fails, the operator must return a bounded failure posture rather than silently substituting another source family.

**Persistence and auditability**

- R17. The pack must define the expected persistence unit for each source family in scope, so expansion persists the smallest useful reusable slice.
- R18. The operator must record an expansion audit trail that explains why expansion was allowed, which source family was chosen, what search stage was attempted, and why the accepted source passed policy.
- R19. The expansion audit trail must also make bounded failure explainable when the operator stops without finding acceptable canonical support.

**Evaluation**

- R20. Ledger evals must measure wrong-source drift as a first-class failure mode.
- R21. Ledger evals must measure first-run expand success under bounded canonical expansion.
- R22. Ledger evals must separately surface query-efficiency failures within the correct source family.
- R23. The first version must prove improvement on real benchmarks that are not biased toward the archive's current local coverage.

---

## Actors

- A1. Archive operator agent that must expand from canonical sources without drifting or wasting search effort.
- A2. Domain expert who configures packs and wants expansion behavior to be reusable across indexes.
- A3. Evaluator or maintainer who needs to inspect why expansion succeeded, failed, or drifted.

---

## Key Flows

- F1. Right-source first-pass success
  - **Trigger:** Local archive support is weak for a question that is in bounds for expansion.
  - **Actors:** A1
  - **Steps:** The operator classifies the question shape, loads the pack's allowed source-family policy, selects the preferred canonical source family, issues bounded first-pass queries, accepts a policy-compliant source, persists the atomic slice, and answers.
  - **Outcome:** The archive grows from the right canonical layer without widening search unnecessarily.

- F2. Right-source bounded refinement
  - **Trigger:** The first-pass canonical queries are weak or imprecise.
  - **Actors:** A1
  - **Steps:** The operator stays inside the same allowed source family, applies one bounded refinement pass, and either finds acceptable support or reaches the stop condition.
  - **Outcome:** Search improves without degenerating into open-ended exploration.

- F3. Wrong-source rejection
  - **Trigger:** A seemingly relevant page appears from a source family that is not allowed for the current question shape.
  - **Actors:** A1, A3
  - **Steps:** The source acceptance check rejects the page, records the rejection in the audit trail, and continues only within the allowed policy or stops boundedly.
  - **Outcome:** The operator does not answer from the wrong canonical layer.

- F4. Bounded failure
  - **Trigger:** The allowed source family and bounded refinement budget still fail to produce acceptable support.
  - **Actors:** A1, A3
  - **Steps:** The operator stops after the configured budget, records why the bounded search failed, and returns a non-answer or other policy-allowed failure posture.
  - **Outcome:** Ledger fails conservatively instead of widening silently or inventing support.

---

## Acceptance Examples

- AE1. Covers R2, R3, R4, R7.
  - **Given:** A legal-rule question whose pack says only one canonical legislation source family is allowed.
  - **When:** The operator decides how to expand.
  - **Then:** It selects that source family and does not use other official sources even if they look easier to search.

- AE2. Covers R8, R9, R10, R11.
  - **Given:** A question whose canonical source family is correct but whose first-pass query is weak.
  - **When:** The operator searches.
  - **Then:** It performs a bounded refinement inside that same source family rather than issuing a long trail of low-quality or repetitive queries.

- AE3. Covers R13, R14, R16.
  - **Given:** A plausible page from a non-allowed source family appears during expansion.
  - **When:** The operator evaluates it.
  - **Then:** The source acceptance check rejects it and the operator does not answer from it.

- AE4. Covers R15, R18, R19.
  - **Given:** The correct source family still does not yield acceptable support within the allowed query budget.
  - **When:** The operator reaches the stop condition.
  - **Then:** It fails boundedly and records why it stopped instead of widening the search space silently.

- AE5. Covers R20, R21, R22, R23.
  - **Given:** A benchmark set intentionally biased away from current local archive coverage.
  - **When:** Ledger runs in expand mode with bounded canonical expansion enabled.
  - **Then:** The reports show wrong-source drift, query-efficiency behavior, and first-run expand success as separate measurable outcomes.

---

## Success Criteria

- S1. Real benchmark runs show a lower wrong-source rate than the current expansion behavior.
- S2. Real benchmark runs show fewer obviously wasted or repetitive queries within the correct source family.
- S3. First-run expand success improves on bounded canonical benchmarks without broadening to disallowed source families.
- S4. The operator can explain both success and bounded failure in a compact audit trail that a maintainer can inspect.
- S5. The contract is reusable enough that a second source family can adopt it without inventing a new expansion theory.

---

## Scope Boundaries

### Deferred for later

- Rich operator memory that learns search heuristics primarily from prior runs instead of from pack policy.
- Broad fallback policies that widen from the canonical source family to other official sources.
- Sophisticated search optimization beyond the first bounded refinement loop.

### Outside this feature's identity

- Generic web search as the default archive-growth strategy.
- Source-family policy that is only implicit in prompts or operator intuition.
- Treating "found some official page" as equivalent to canonical support.

---

## Dependencies / Assumptions

- Domain packs remain the main reusable configuration surface for archive behavior.
- Operators already have an archive-first flow and an in-bounds expansion path to extend.
- Eval infrastructure can be expanded to score source-family and query-discipline behavior separately.
- Benchmark sets can be intentionally chosen to avoid flattering current archive-local coverage.

---

## Outstanding Questions

### Resolve Before Planning

- Which question-shape taxonomy is the minimum useful v1 set for driving source-family policy without overfitting one domain?
- How much of the canonical search plan should be declarative pack data versus richer source-family guidance text?

### Deferred to Planning

- Where should the source acceptance checks and search-plan contract hook into the existing operator/check surfaces?
- What is the most compact audit record shape that still explains query stages, source rejection, and bounded failure?

---

## Sources / Research

- `STRATEGY.md`
- `docs/brainstorms/2026-05-27-unknown-weak-slice-pre-answer-detection-requirements.md`
- `docs/evals/2026-05-28-dr-only-portuguese-legal-benchmark.md`
- `docs/evals/2026-05-28-dr-only-edge-case-portuguese-legal-benchmark.md`
- `skills/domain-archive-pack-builder/references/expansion-recipes.md`
- `skills/domain-archive-pack-builder/scripts/check_expansion_plan.py`
- `skills/domain-archive-pack-builder/scripts/scaffold_domain_pack.py`
- `skills/archive-index-builder/scripts/scaffold_archive_index.py`
- `skills/archive-evals/SKILL.md`
- `skills/archive-evals/references/buckets-and-reporting.md`
- `skills/archive-evals/references/scenario-schema.md`
