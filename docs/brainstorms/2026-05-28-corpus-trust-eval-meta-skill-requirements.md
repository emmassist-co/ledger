---
date: 2026-05-28
topic: corpus-trust-eval-meta-skill
---

# Corpus Trust Eval Meta-Skill

## Summary

Define a Ledger meta-skill that creates and maintains eval suites for a specific corpus and archive, so Ledger can judge whether an ordinary agent operating that archive is trustworthy enough on real questions. The trust bar is not “the eval questions exist”; it is passing a threshold on real corpus-shaped questions that exercise retrieval, exceptions, time/version awareness, and safe archive growth behavior.

## Problem Frame

Ledger’s archive-building meta is only useful if it can prove that ordinary agents using a generated archive are actually trustworthy on that corpus. Today the archive and domain-pack system can shape operator behavior, and local evals already exist, but the trust surface is still too hand-built and corpus-specific. Without a reusable eval-building capability, each archive proves trust ad hoc, which makes it hard to know whether the archive-building meta itself is working.

## Key Decisions

- **Trust threshold over eval existence.** The meta-skill’s job is to tell us whether an agent is trustworthy enough on a corpus, not merely to scaffold scenarios.
- **Ordinary agent, real archive.** The eval suite must run against a normal agent operating inside the archive workspace, following local skills and deterministic gates.
- **Mixed real-question coverage.** A trustworthy corpus needs a mix of direct rule lookups, exception-heavy questions, time/version-sensitive questions, and case-shaped research prompts.

## Actors

- A1. **Primary actor:** A Ledger maintainer or archive builder who needs to know whether a generated archive is trustworthy on its corpus.
- A2. **Evaluated actor:** An ordinary agent operating inside the archive with local skills, scripts, and archive rules.

## Key Flows

- F1. **Corpus to trust suite**
  - **Trigger:** A new archive or corpus is ready for trust evaluation.
  - **Outcome:** The meta-skill generates a corpus-specific eval suite with real-question coverage, scoring rules, and trust thresholds.

- F2. **Trust suite to agent verdict**
  - **Trigger:** The suite is run against an ordinary agent using the archive.
  - **Outcome:** The system reports whether the agent is trustworthy enough on that corpus, plus where it fails.

- F3. **Failure to hardening loop**
  - **Trigger:** The agent fails threshold on one or more real questions.
  - **Outcome:** The failing questions become durable regressions and the trust report identifies which failure family needs archive or skill hardening.

## Requirements

**Eval-suite generation**

- R1. The meta-skill must generate a corpus-specific eval suite whose purpose is to judge agent trustworthiness on that corpus.
- R2. The suite must include real corpus-shaped questions rather than only synthetic retrieval prompts.
- R3. The suite must cover, at minimum, these question families when material to the corpus:
  - direct rule lookups
  - exception-heavy questions
  - time/version-sensitive questions
  - case-shaped research prompts

**Operator-under-test**

- R4. The suite must run against an ordinary agent operating inside the archive workspace, using the local `AGENTS.md`, local skill, and deterministic archive scripts.
- R5. The suite must evaluate both process and outcome: a plausible answer with off-policy archive behavior must not count as a clean pass.
- R6. The suite must exercise both local-support questions and weak-local-support questions that require canonical expansion and persistence when that behavior is part of the archive contract.

**Trust scoring**

- R7. The suite must define an explicit trust threshold for the corpus, not only per-question grades.
- R8. The threshold must be based on real-question pass rate, with stricter emphasis on critical-path or golden cases where failure would most damage trust.
- R9. The suite must fail the agent when it misses a material exception, answers from the wrong legal time/version state, overlooks a decisive relevant point, or presents unsupported certainty.

**Failure output**

- R10. The suite must group failures by family so the maintainer can see whether the problem is retrieval, exception coverage, temporal awareness, archive growth behavior, or answer posture.
- R11. Failed real questions must be reusable as durable regressions for that corpus.
- R12. The trust report must make clear whether the agent is “trustworthy enough,” “not yet trustworthy,” or “passes only with visible caveats.”

## Acceptance Examples

- AE1. **Covers R3, R9.**
  - A corpus includes a rule whose base answer is easy but whose exception changes the result.
  - The generated suite includes that question in the exception-heavy family and the agent fails if it returns only the base rule.

- AE2. **Covers R3, R9.**
  - A corpus includes a rule that changed recently.
  - The generated suite includes a time/version-sensitive question and the agent fails if it answers from the wrong version or omits the temporal caveat.

- AE3. **Covers R4, R5, R6.**
  - A weak-local-support question is included.
  - The agent is expected to query the archive, expand canonically, persist reusable material, rebuild, and answer with the correct posture; skipping that process counts against the result even if the final prose sounds plausible.

- AE4. **Covers R7, R8, R12.**
  - The suite runs on a corpus with mixed question families.
  - The final report states whether the corpus passes its trust threshold and shows golden-case and critical-path health separately from overall score.

## Success Criteria

- Ledger can apply the meta-skill to a new archive and get a trust verdict on whether an ordinary agent is good enough on that corpus.
- Trust reports are specific enough to tell maintainers why an archive is not yet safe to rely on.
- The eval suite gets better over time because failed real questions become durable regressions rather than one-off discoveries.

## Scope Boundaries

- This work is not about building a general legal benchmark independent of archive operation.
- This work is not about proving autonomous final legal conclusions for case outcomes.
- This work is not about optimizing for broad benchmark score at the expense of corpus-specific trustworthiness.

## Dependencies / Assumptions

- New archives have enough local operator guidance and deterministic archive checks that an ordinary agent can be meaningfully evaluated against them.
- Real corpus-shaped questions can be sourced from existing archive material, user-seeded questions, or known difficult slices.
- Different corpora may need different trust thresholds, but the meta-skill should produce the same evaluation shape across them.

## Outstanding Questions

- OQ1. What is the minimum threshold shape Ledger should standardize across corpora: overall pass rate only, or overall pass rate plus golden/critical-path minimums?
- OQ2. How much of the “ordinary agent run” should be replayed automatically versus reviewed through captured evidence after the run?
- OQ3. Should the first generated suites prefer a small high-signal set of real questions or a broader mixed set with lower per-case depth?

## Sources / Research

- `STRATEGY.md`
- `archive-index/TESTING.md`
- `archive-index/AGENTS.md`
- `archive-index/archive-evals/`
- `docs/evals/2026-05-28-portuguese-legal-qa-seed-benchmark-results-growing-operator.md`
- `docs/evals/2026-05-28-dr-only-edge-case-portuguese-legal-benchmark.md`
