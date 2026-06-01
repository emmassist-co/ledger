---
date: 2026-06-01
topic: dr-currentness-supersession-meta-skill
---

# DR Currentness And Supersession Meta-Skill

## Summary

Extend Ledger's existing domain-pack and verifier architecture so generated archives for Portuguese `diariodarepublica.pt` legislation can answer current-law questions more safely. The first version should detect when relied-on support is outdated or superseded, force refresh-backed proof for current-law answers, and block confident output when the archive cannot prove the cited slice is still current.

---

## Problem Frame

Ledger already has a strong split between agent judgment and deterministic rails. Domain packs teach source families, persistence posture, support hierarchy, bounded expansion, freshness posture, and answer contract behavior. Deterministic checks already constrain coverage, provenance, support strength, exact wording, confirmation boundaries, and eval posture.

That is not yet enough for current-law legal questions. A human relying on the agent's answer still has to manually recheck the canonical source to make sure the cited rule has not been updated or superseded. The current archive contract can say "refresh before answer" and "declare `verified_at`," but that is weaker than proving that the specific relied-on slice is still the current governing text. The unacceptable failure is not only hallucination. It is giving a plausible answer from a provision version that is no longer current.

The gap is therefore not "build a new runtime." The gap is to extend the existing meta-skill architecture with a temporal/currentness subsystem that ordinary archive agents can use through generated rules and deterministic gates.

---

## Key Decisions

- **Current-law only in v1.** The first version should handle "what is the law now?" questions for Portuguese DR legislation. Historical or as-of-date questions are deferred because they require a broader temporal model and would dilute the first proof point.

- **Extend the existing meta-pack architecture.** The new capability should be generated through domain-pack outputs, operator guidance, verifier checks, and eval scenarios rather than as a separate workflow engine or legal-specific runtime.

- **Superseded-slice detection is part of the bar.** V1 should not stop at "the source was refreshed recently." It should aim to detect when previously relied-on support is no longer current and block confident current-law answers until the current slice is re-established.

- **Human-visible proof bundle is part of the product.** The user-facing surface should make it fast for a human to trust the answer by showing at least when the source was checked and the canonical link used for the refresh-backed answer.

---

## Actors

- A1. **Primary actor:** Human relying on an agent's answer to a current-law Portuguese legislation question.
- A2. **Operating actor:** Ordinary archive agent answering inside a Ledger archive workspace using generated local skills and deterministic checks.
- A3. **Maintainer actor:** Archive maintainer or domain expert who uses Ledger meta-skills to create and improve the archive contract for DR legislation.

---

## Key Flows

- F1. **Current-law answer with valid current support**
  - **Trigger:** A human asks a current-law question about Portuguese legislation.
  - **Actors:** A1, A2
  - **Steps:** The agent classifies the question as current-law, checks local support, refreshes through the canonical DR path when required, verifies that the relied-on slice is still current, and answers with a proof bundle.
  - **Outcome:** The answer includes the governing rule with proof that is quick for the human to inspect.

- F2. **Previously relied-on support is outdated**
  - **Trigger:** The archive contains a locally useful extract or derived answer path, but the relevant legal text has changed.
  - **Actors:** A1, A2
  - **Steps:** The agent or deterministic checks detect that the prior relied-on slice is outdated or superseded, refuse to treat it as current support, and force refresh-backed retrieval of the current governing text before a current-law answer can complete.
  - **Outcome:** The system blocks false confidence from stale local knowledge.

- F3. **Currentness cannot be proven**
  - **Trigger:** A current-law question requires proof of currentness, but the archive cannot confirm that the relied-on slice is still current.
  - **Actors:** A1, A2
  - **Steps:** The agent follows the generated operator guidance, hits the currentness gate, and returns a constrained answer posture rather than a confident current-law answer.
  - **Outcome:** The human sees that the system could not prove currentness and is not misled into trusting stale output.

---

## Requirements

**Meta-skill outputs**

- R1. Ledger must extend its domain-pack meta-skill outputs so a generated archive can express currentness and supersession rules for Portuguese `diariodarepublica.pt` legislation.
- R2. The generated contract must distinguish current-law questions from other question shapes and apply stronger currentness requirements to that question shape.
- R3. The generated contract must define how a DR legislation slice is checked for currentness before a decisive current-law answer is allowed.
- R4. The generated contract must define how previously relied-on support is recognized as outdated or superseded for current-law use.

**Deterministic gates**

- R5. Ledger must add deterministic checks that can block a current-law answer when the archive cannot prove the relied-on slice is still current.
- R6. The deterministic layer must treat "recently checked" and "still current" as distinct outcomes.
- R7. The deterministic layer must be able to invalidate local support for current-law answering when it no longer matches the current canonical DR state.
- R8. The deterministic layer must feed its currentness and supersession results into the answer posture and eval layers instead of leaving them as silent internal state.

**Operator behavior**

- R9. An ordinary archive agent operating inside the generated archive must be able to follow local guidance and deterministic checks to produce a safe current-law answer without bespoke repo archaeology.
- R10. For current-law questions, the generated operator guidance must require refresh-backed proof before the agent may present a confident decisive answer.
- R11. If currentness cannot be proven, the generated contract must force a constrained answer posture rather than allowing unsupported certainty.

**Human-visible proof**

- R12. A current-law answer that passes the currentness gate must include a proof bundle that shows at least when the source was checked and the canonical link used.
- R13. The proof bundle must make it clear that the answer is grounded in the current canonical DR source rather than only in older local archive material.

**Eval and trust**

- R14. Ledger must generate eval scenarios for Portuguese DR legislation that fail when the system answers from outdated or superseded support.
- R15. The trust/eval layer must report temporal/currentness failures as a distinct failure family rather than hiding them under generic retrieval or grounding misses.

---

## Acceptance Examples

- AE1. **Covers R3, R5, R12.**
  - **Given:** A current-law question about a Portuguese statutory provision and an archive that can refresh through the canonical DR path.
  - **When:** The agent answers the question.
  - **Then:** The answer includes a proof bundle showing when the source was checked and the canonical DR link used for the current answer.

- AE2. **Covers R4, R7, R14.**
  - **Given:** The archive contains an older relied-on slice for a provision that has since been updated.
  - **When:** The agent tries to answer a current-law question from that old support.
  - **Then:** The deterministic currentness layer blocks use of the stale slice as current support and the eval suite marks that stale-answer path as a failure.

- AE3. **Covers R6, R11.**
  - **Given:** A source was refreshed recently but the system still cannot prove that the relied-on local slice matches the current governing text.
  - **When:** The agent tries to provide a confident current-law answer.
  - **Then:** The system distinguishes "recently checked" from "still current" and prevents unsupported certainty.

- AE4. **Covers R9, R10.**
  - **Given:** An ordinary agent is dropped into the generated archive workspace.
  - **When:** It handles a current-law DR question using only the local generated guidance and deterministic checks.
  - **Then:** It follows the currentness workflow correctly without needing corpus-specific handholding outside the generated archive surface.

---

## Success Criteria

- The archive can no longer pass current-law DR questions by relying on stale local support that has been updated or superseded.
- A human relying on the answer can quickly inspect the proof bundle and see when the source was checked and which canonical DR link was used.
- Ledger's trust/eval layer can measure whether the archive is improving specifically on temporal/currentness safety, not only on generic retrieval quality.
- The first version proves that Ledger can extend domain packs and deterministic rails for temporal safety without replacing the agent-native architecture with a rigid runtime.

---

## Scope Boundaries

### Deferred For Later

- Historical or as-of-date legal questions
- Full amendment-lineage explanation for every answer
- Generalization beyond Portuguese `diariodarepublica.pt` legislation

### Outside This Product's Identity

- Autonomous final legal conclusions for case outcomes
- Replacing agent judgment with a legal-specific workflow engine
- Turning Ledger core into a hardcoded corpus-specific runtime

---

## Dependencies / Assumptions

- Portuguese `diariodarepublica.pt` provides enough canonical structure for the first version to check currentness and detect at least some updated or superseded relied-on slices.
- The current domain-pack and verifier architecture remains the main product surface; this work extends that architecture rather than replacing it.
- A useful first version can prove current-law safety improvement without needing a fully general legal version graph.

---

## Outstanding Questions

### Deferred To Planning

- OQ1. What is the minimum generated temporal model needed for v1: currentness flags only, supersession pointers, or a thinner provision-version identity layer?
- OQ2. Which deterministic checks should be introduced first so the repo gets measurable safety gain without overbuilding the verifier framework?
- OQ3. How narrow should the DR proving ground be at first if source structure varies across legislation families?

---

## Sources / Research

- `STRATEGY.md`
- `docs/brainstorms/2026-05-27-domain-pack-product-surface-requirements.md`
- `docs/brainstorms/2026-05-28-corpus-trust-eval-meta-skill-requirements.md`
- `docs/brainstorms/2026-05-28-legal-research-assistant-confidence-bar-requirements.md`
- `docs/plans/2026-05-27-001-feat-self-growing-canonical-archives-plan.md`
- `docs/plans/2026-05-28-001-feat-meta-index-practices-plan.md`
- `docs/plans/2026-05-28-003-feat-corpus-trust-eval-meta-skill-plan.md`
- `skills/archive-index-builder/SKILL.md`
- `skills/archive-index-builder/references/verifier-toolkit.md`
- `skills/domain-archive-pack-builder/SKILL.md`
- `skills/domain-archive-pack-builder/references/domain-pack-contract.md`
