---
date: 2026-05-27
topic: unknown-weak-slice-pre-answer-detection
title: "Unknown Weak Slice Pre-Answer Detection"
---

# Unknown Weak Slice Pre-Answer Detection

## Summary

Add a pre-answer weak-slice check that runs after retrieval and before the archive chooses `answer` versus `expand`. It should use domain-pack expectations as the primary definition of target-quality support, compare the currently found local support against that target, and safely flag `likely_below_target` early enough to change the live answer path and auto-register a provisional weak-slice entry.

---

## Problem Frame

Ledger is now good at handling known weak slices. The archive can record `support_gaps`, detect them with `check_coverage_state`, and force `expand` when `auto_expand_when_below_target` is enabled. That is a real step forward, and the current flagship archive now proves this on concrete scenarios.

The remaining failure is earlier in the flow. The archive can retrieve something relevant, treat it as sufficient, and only later realize that the decisive support was incomplete. The most concrete example is a legal slice where the retrieved article looks right but does not carry the exception that actually determines the answer. In those moments the archive is not wrong because retrieval failed. It is wrong because it treated partial local support as complete before it had an explicit chance to challenge that assumption.

The current system only handles this well when the weakness is already known. Unknown weak slices still become visible mainly through first-contact failure, manual eval work, or manual `coverage-ledger` edits. That leaves a gap between the product claim and the actual operator behavior: Ledger can honor known weakness, but it is still too passive at noticing new likely weakness before committing to an answer path.

---

## Key Decisions

- **KD1. Pre-answer is the right intervention point.** The first version should not try to classify weakness at retrieval-ranking time, and it should not wait until after final synthesis. It should run after retrieval has produced candidate support and before the archive commits to `answer` versus `expand`.
- **KD2. Domain-pack expectations define the bar.** The detector should not decide “good enough” from local heuristics alone. The domain pack defines the required support class, granularity, and answer posture for the question shape; local archive signals only test whether current evidence meets that bar.
- **KD3. Bias toward safe false positives.** The first version should tolerate some unnecessary `expand` decisions if that materially reduces confident misses on weak support. The product risk to reduce is premature completion, not occasional extra caution.
- **KD4. Generic mechanism, concrete proving ground.** The first version should apply across source families from day one, but the motivating failure and early proof should be anchored in statutory and exception-sensitive slices because that is where the failure is easiest to observe and most costly to miss.
- **KD5. Detection should compound archive self-knowledge.** When the detector flags a likely weak slice, the archive should not forget it after the current answer path. It should write a provisional `coverage-ledger` entry so later runs can benefit immediately, even before a human curates the slice.

---

## Requirements

- R1. The archive must run a pre-answer weak-slice check after retrieval and before choosing `answer`, `expand`, or `ask_user`.
- R2. The pre-answer check must classify at least three outcomes: `clear`, `known_below_target`, and `likely_below_target`.
- R3. The pre-answer check must use domain-pack expectations as the primary definition of target quality for the current question shape, including support class, granularity, exact-wording posture, and any answer-mode rules.

**Decision behavior**

- R4. When the check returns `clear`, the archive may continue toward `answer` subject to the existing policy and verifier checks.
- R5. When the check returns `known_below_target`, the archive must preserve the current behavior of preferring `expand` unless the real blocker is missing user facts or another explicitly allowed non-expand action.
- R6. When the check returns `likely_below_target`, the archive must treat that result as strong enough to block a straight-to-`answer` path in the first version.
- R7. The first version must favor safe-side detection over precision, meaning it may over-flag some slices if that reduces premature completion on weak support.

**Signal model**

- R8. The first version must combine domain-pack expectations with local archive signals already available in the live path, rather than requiring a heavyweight new retrieval or parsing subsystem.
- R9. The detector must be able to identify at least the concrete failure where the retrieved legal article family is relevant but the decisive exception or qualification is not locally supported strongly enough.
- R10. The detector must remain generic across source families, even if some early signal shapes are stronger for statutory/legal material than for other domains.

**Archive memory**

- R11. When the detector returns `likely_below_target`, the archive must auto-register a provisional weak-slice entry in `domain/coverage-ledger.yaml`.
- R12. The minimum day-one provisional entry must include topic labels, question shape, and a reason for the likely weakness.
- R13. Provisional entries must be distinguishable from already-confirmed support gaps so the archive can carry suspicion without pretending the gap has been manually confirmed.
- R14. The workflow must define how a provisional entry later becomes confirmed, cleared, or superseded by stronger local support.

**Product boundaries**

- R15. This feature must change the live answer-path decision, not only reporting or benchmark output.
- R16. This feature must not require a heavyweight runtime or orchestrator layer; it should fit the current Ledger shape of pack rules, local guidance, helper checks, and archive-local state.
- R17. This feature must not claim to solve full `expand -> persist -> answer` closure by itself; it is specifically about earlier detection and safer routing.

---

## Actors

- A1. Archive operator agent using the local archive and pack rules to answer real questions.
- A2. Domain expert or maintainer who reviews provisional weak-slice entries and strengthens the archive over time.
- A3. Planner or evaluator who needs the archive behavior to be explainable, testable, and reusable across other archives.

---

## Key Flows

- F1. Pre-answer clear path
  - **Trigger:** Retrieval finds candidate local support for a question.
  - **Actors:** A1
  - **Steps:** The archive classifies the question shape, reads the pack’s support target, compares the retrieved/opened support against that target, gets `clear`, and continues toward `answer`.
  - **Outcome:** The archive answers without unnecessary expansion, and the decision is still justified by the same pack-aware check.

- F2. Known weakness path
  - **Trigger:** Retrieval finds support for a topic that is already in `coverage-ledger.yaml`.
  - **Actors:** A1
  - **Steps:** The archive runs the pre-answer check, sees `known_below_target`, and routes to `expand` or another explicitly allowed non-expand action.
  - **Outcome:** Existing known-gap behavior stays intact and remains the stronger, deterministic case.

- F3. Unknown likely weakness path
  - **Trigger:** Retrieval finds seemingly relevant local support, but the support does not meet the pack’s expected level for the question shape.
  - **Actors:** A1, A2
  - **Steps:** The archive returns `likely_below_target`, blocks a straight-to-`answer` path, auto-registers a provisional weak-slice entry, and routes to `expand` or `ask_user` per policy.
  - **Outcome:** The archive avoids premature completion and carries forward new self-knowledge for later runs.

- F4. Provisional-entry closure path
  - **Trigger:** Later archive work materializes stronger support or proves the suspicion unnecessary.
  - **Actors:** A1, A2
  - **Steps:** The archive or maintainer updates the provisional entry to confirmed, cleared, or superseded based on later evidence.
  - **Outcome:** `coverage-ledger.yaml` becomes a living memory of both known and newly discovered weak slices instead of a static manual list.

---

## Acceptance Examples

- AE1. Covers R1, R2, R3, R8.
  - **Given:** A question whose candidate support has already been retrieved locally.
  - **When:** The archive is about to choose `answer` versus `expand`.
  - **Then:** It runs a pack-aware weak-slice check and produces one of `clear`, `known_below_target`, or `likely_below_target`.

- AE2. Covers R6, R7, R9.
  - **Given:** A legal question where the archive retrieves the right article family but lacks strong local support for the decisive exception.
  - **When:** The pre-answer check compares current support against the pack’s expected support target.
  - **Then:** It returns `likely_below_target` and blocks a direct-answer path, even if retrieval looked superficially successful.

- AE3. Covers R11, R12, R13.
  - **Given:** A slice flagged `likely_below_target` for the first time.
  - **When:** The archive records the suspicion.
  - **Then:** It writes a provisional entry into `domain/coverage-ledger.yaml` with topic labels, question shape, and a reason, without pretending the gap is already fully confirmed.

- AE4. Covers R10, R15, R16.
  - **Given:** Two archives with different source families and different pack-defined support expectations.
  - **When:** Each archive runs the same pre-answer weak-slice mechanism.
  - **Then:** The mechanism stays generic while the pack-specific support target changes what counts as sufficient.

- AE5. Covers R14, R17.
  - **Given:** A provisional weak-slice entry created by the detector.
  - **When:** Later work either materializes stronger support or shows that the suspicion was unnecessary.
  - **Then:** The entry can be confirmed, cleared, or superseded, and this feature is still understood as earlier detection rather than full autonomous closure.

---

## Success Criteria

- S1. The flagship archive catches at least one concrete weak-slice miss before committing to a direct-answer path.
- S2. The archive writes provisional weak-slice memory that later runs can reuse without a human manually discovering the same weakness again.
- S3. Eval scenarios can distinguish `known_below_target` from `likely_below_target` and verify that both alter the live answer path appropriately.
- S4. The first version materially reduces “relevant artifact found, but decisive support was incomplete” failures without forcing a heavyweight orchestrator design.

---

## Scope Boundaries

### Deferred for later

- Rich provisional-entry payloads such as candidate artifact IDs, generated remediation plans, or confidence scores.
- Sophisticated retrieval-time ranking heuristics that try to detect weak slices before artifact-level comparison.
- Full automation for confirming or clearing provisional entries without later evidence or review.

### Outside this feature’s identity

- A generic runtime controller that replaces the agent’s judgment.
- Full autonomous `expand -> persist -> answer` closure.
- Solving all archive quality issues through retrieval ranking alone.

---

## Dependencies / Assumptions

- The current domain-pack and answer-contract surfaces remain the source of truth for support expectations and answer posture.
- The archive already has a live place to persist self-knowledge in `domain/coverage-ledger.yaml`.
- The first version can rely on signals already present in the local answer path rather than requiring broad new corpus ingestion or parser-heavy infrastructure.
- Some source families will produce weaker early signals than statutory/legal material; the generic mechanism is still expected to hold, even if the first proving cases are legal.

---

## Outstanding Questions

### Resolve Before Planning

- How should provisional weak-slice entries be represented so they are clearly separate from confirmed support gaps without complicating the operator workflow too much?
- What exact local signal set is the minimum viable first-version comparator between pack expectation and current support?

### Deferred to Planning

- Should the pre-answer weak-slice check live as a new helper command, an extension of `run_archive_check.py`, or a smaller internal wrapper around existing checks?
- How should eval reports present the difference between `known_below_target` and `likely_below_target` without obscuring the main pass/fail posture?

---

## Sources / Research

- `docs/plans/2026-05-27-001-feat-self-growing-canonical-archives-plan.md`
- `docs/brainstorms/2026-05-27-domain-pack-product-surface-requirements.md`
- `STRATEGY.md`
- `archive-index/domain/coverage-ledger.yaml`
- `archive-index/recipes/answer-contract.yaml`
- `archive-index/domain/ENRICHMENT_PROTOCOL.md`
- `archive-index/archive-evals/reports/latest.json`
- `archive-index/archive-evals/scenarios/grounding-art-ce-pontos.json`
- `archive-index/archive-evals/scenarios/grounding-art-ce-probatorio.json`
- `archive-index/archive-evals/scenarios/grounding-ext-cirs-art43-resident-gains-current.json`
