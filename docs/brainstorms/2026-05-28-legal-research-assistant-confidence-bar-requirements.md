---
date: 2026-05-28
topic: legal-research-assistant-confidence-bar
---

# Legal Research Assistant Confidence Bar

## Summary

Define the first trustable product shape for a lawyer-facing assistant as a research copilot, not a case-conclusion engine. The assistant should take a legal question, case summary, or directed query set and return the governing rule, relevant exceptions, temporal caveats, and official citations clearly enough that a lawyer can rely on it for discovery and compilation work.

## Problem Frame

A practicing lawyer answering case-shaped questions does not start by wanting a polished AI conclusion. She starts by needing the right legal sources, the relevant exceptions, and the current temporal state of the law, then compares them before answering. The unacceptable failure is not just “wrong answer”; it is missing an exception, overlooking that a rule changed, or flattening a nuanced legal picture into a confident but incomplete summary.

## Key Decisions

- **Research support, not legal conclusion.** The first target is an assistant that gathers and organizes the law safely enough for a lawyer to use, not one that autonomously settles the case outcome.
- **Law-first trust bar.** Official sources, exception coverage, and time/version awareness matter more than conversational fluency or speed alone.
- **Case-shaped input is in scope.** The assistant must handle plain-language questions, case summaries, and directed research tasks, not only article lookup from known references.

## Actors

- A1. **Primary actor:** A lawyer working inside a bank.
- A2. **Assistant actor:** A research assistant that gathers the rule, exceptions, and citations from official sources.

## Key Flows

- F1. **Plain-language question to research bundle**
  - **Trigger:** The lawyer asks how a legal rule works.
  - **Outcome:** The assistant returns the governing rule, relevant exceptions, temporal caveats, and official citations.

- F2. **Case summary to scoped research**
  - **Trigger:** The lawyer gives a short case summary and asks what law needs to be checked.
  - **Outcome:** The assistant identifies the likely governing provisions, exceptions, and factual gaps that matter for the case.

- F3. **Directed query set to comparison output**
  - **Trigger:** The lawyer asks the assistant to gather and compare a few articles, provisions, or related references.
  - **Outcome:** The assistant compiles the requested sources and highlights where they align, differ, or create exceptions that matter.

## Requirements

**Research output**

- R1. For an in-scope legal research question, the assistant must return the governing rule from official or archive-approved sources.
- R2. The assistant must surface relevant exceptions, carve-outs, or adjacent provisions that could materially change the lawyer’s understanding of the rule.
- R3. The assistant must distinguish the core rule from case application, rather than collapsing both into a single confident conclusion.

**Temporal and source discipline**

- R4. The assistant must surface when a rule is version-sensitive, amended, repealed, or otherwise time-dependent.
- R5. The assistant must cite the official source or archive-backed extract used for each decisive rule statement.
- R6. The assistant must make missing support visible instead of filling gaps with plausible but unsupported synthesis.

**Case-shaped usefulness**

- R7. The assistant must accept three input shapes: a plain-language legal question, a case summary, or a directed request to gather and compare specified legal materials.
- R8. For case summaries, the assistant must call out factual gaps that prevent safe case-specific application when those gaps matter.
- R9. The assistant must produce output that a lawyer can reuse as research material, not only as conversational prose.

**Trust boundary**

- R10. The assistant must not present a final legal conclusion for a case as settled when the available support is only enough for research or provisional analysis.
- R11. The assistant must make the difference between “rule found,” “exception found,” and “case outcome still requires lawyer judgment” visible in the output.

## Acceptance Examples

- AE1. **Covers R2, R4, R5.**
  - A lawyer asks a general question about how a rule works.
  - The assistant returns the current governing provision, flags that the rule changed after a recent amendment, and includes the official citation for the current version.

- AE2. **Covers R2, R8, R10, R11.**
  - A lawyer gives a case summary and asks whether a rule applies.
  - The assistant returns the governing rule plus the exception that could change the answer, then explicitly says the case outcome depends on missing facts rather than pretending the answer is settled.

- AE3. **Covers R7, R9.**
  - A lawyer asks the assistant to gather and compare several articles or provisions.
  - The assistant returns a structured bundle showing the articles, the main points of comparison, and any exception or temporal mismatch that matters.

## Success Criteria

- The assistant reliably reduces the lawyer’s time spent gathering first-pass legal material from notes plus official sources.
- The assistant’s research outputs are reviewable and reusable because they separate rule, exceptions, time/version notes, and source citations.
- The failure rate for missed exceptions, stale-law flattening, and unsupported confident statements is low enough that a lawyer would willingly use it as a daily research copilot.

## Scope Boundaries

- The first release does not aim to replace the lawyer’s own legal judgment on case outcomes.
- The first release does not aim to be a general-purpose legal chatbot across all possible domains.
- Broader autonomous case analysis is deferred until the research-copilot trust bar is passed consistently.

## Dependencies / Assumptions

- The product depends on archive-backed or otherwise official-source-first retrieval with strong enough support to surface exceptions and temporal changes.
- The target workflow assumes the lawyer is willing to review compiled research output but does not want to spend the same time manually discovering the material every time.
- Initial trust should be established in the narrower domain where the user actually works, rather than across all law at once.

## Outstanding Questions

- OQ1. What legal slice inside the bank-law workflow should be the first production domain, so exception coverage can be judged on a realistic corpus instead of on broad legal generality?
- OQ2. What output format is most useful in her day-to-day work: concise research note, structured citation bundle, or comparison table?

## Sources / Research

- `STRATEGY.md`
- `archive-index/AGENTS.md`
- `archive-index/TESTING.md`
- `archive-index/skills/pt-parliament-legal-grounding-operator/SKILL.md`
