---
name: Ledger
last_updated: 2026-05-28
---

# Ledger Strategy

## Target problem

Agents need answers that live inside very large canonical source systems, but those systems are too big and too interconnected to ingest upfront. Even when the agent knows the right authority, canonical paths are hard to navigate, references force deeper follow-on lookup, and getting useful answers usually requires lots of custom parsing, navigation, and query code instead of an agent-native way to build local knowledge on demand.

## Our approach

Ledger makes the archive workspace the agent's operating environment. Instead of replacing the agent with a workflow engine or writing bespoke parsers for each source, Ledger keeps judgment, synthesis, and expansion decisions in the agent and skill layer, while scripts enforce the deterministic gates: coverage checks, persistence rules, indexing, and audits.

## Who it's for

**Primary:** Domain experts setting up a corpus for agents - They're hiring Ledger to let their agent build and operate a high-accuracy domain archive from canonical sources, without needing to hand-build bespoke parsers and full upfront indexes for the whole corpus.

## Key metrics

- **Reliability rate** - Percent of evaluated answers judged grounded and non-hallucinated; measured through archive evals.
- **Canonical support rate** - Share of real questions answered with cited canonical support; measured through evaluation and answer reports.
- **Expansion success rate** - When local coverage is missing, how often the agent finds and materializes the right canonical slice; measured through archive operation logs and eval runs.

## Tracks

### Recipe and domain-pack system

Build the recipe and domain-pack layer that lets a domain expert teach an agent how to operate a bounded archive from canonical sources without bypassing the archive contract.

_Why it serves the approach:_ This is the core mechanism that keeps archive behavior in the skill layer instead of hardcoding source-specific workflow engines.

### Deterministic archive gates

Build narrow scripts and verifiers for the places where judgment should stop: coverage checks, persistence validation, indexing, exact-wording enforcement, and audit trails.

_Why it serves the approach:_ Ledger works when the agent owns reasoning but cannot silently skip the deterministic trust gates.

### Expansion reliability and success

Make question-driven expansion dependable, so when local coverage is thin the agent can efficiently find, acquire, and materialize the right canonical slice.

_Why it serves the approach:_ The product bet depends on agents repeatedly doing `expand -> persist -> answer` inside the archive, not on one-off operator heroics.

## Current Read

As of 2026-05-28, the repo is materially closer to this strategy than it was at the start of the week.

- The domain-pack and helper-check layer is now strong enough to shape normal agent behavior on a live archive.
- The live archive can detect known below-target slices and push the operator toward `expand`, not premature completion.
- The eval layer now measures at least one real `expand_then_answer` case, not only direct-answer retrieval posture.
- The archive direction is now clearer: scripts should own deterministic gates, while the agent and local skill should own reasoning and answer posture.

The remaining strategic gap is no longer “we need a runtime.” It is:

- making the archive workspace feel like the natural place an agent lives, not a pile of helper scripts
- closing live archive content gaps after detection without hardcoding more workflow than necessary
- proving that ordinary agents can repeatedly `expand -> persist -> answer` by following local skills and deterministic gates, without special tester steering
