---
name: Ledger
last_updated: 2026-05-27
---

# Ledger Strategy

## Target problem

Agents need answers that live inside very large canonical source systems, but those systems are too big and too interconnected to ingest upfront. Even when the agent knows the right authority, canonical paths are hard to navigate, references force deeper follow-on lookup, and getting useful answers usually requires lots of custom parsing, navigation, and query code instead of an agent-native way to build local knowledge on demand.

## Our approach

Ledger makes archive-building agent-native instead of parser-native. Instead of fully indexing giant corpora upfront or writing bespoke code for each source, Ledger lets an agent configure a bounded archive from canonical sources, then grow and verify that archive through recipes, rules, and question-driven enrichment as real work appears.

## Who it's for

**Primary:** Domain experts setting up a corpus for agents - They're hiring Ledger to let their agent build and operate a high-accuracy domain archive from canonical sources, without needing to hand-build bespoke parsers and full upfront indexes for the whole corpus.

## Key metrics

- **Reliability rate** - Percent of evaluated answers judged grounded and non-hallucinated; measured through archive evals.
- **Canonical support rate** - Share of real questions answered with cited canonical support; measured through evaluation and answer reports.
- **Expansion success rate** - When local coverage is missing, how often the agent finds and materializes the right canonical slice; measured through archive operation logs and eval runs.

## Tracks

### Recipe and domain-pack system

Build the recipe and domain-pack layer that lets a domain expert teach an agent how to create, navigate, and enrich a bounded archive from canonical sources.

_Why it serves the approach:_ This is the core mechanism that replaces bespoke parser-heavy corpus code with reusable agent guidance.

### Answer evaluation

Build a strong evaluation layer that measures whether Ledger-built archives answer real questions well, with grounded canonical support and low hallucination.

_Why it serves the approach:_ Ledger only works if archive quality is judged by answer quality, not by scaffold completeness or retrieval mechanics alone.

### Expansion reliability and success

Make question-driven expansion dependable, so when local coverage is thin the agent can efficiently find, acquire, and materialize the right canonical slice.

_Why it serves the approach:_ The product bet depends on incremental archive growth through use instead of full upfront indexing.

## Current Read

As of 2026-05-27, the repo is materially closer to this strategy than it was at the start of the day.

- The domain-pack and helper-check layer is now strong enough to shape normal agent behavior on a live archive.
- The live archive can detect known below-target slices and push the operator toward `expand`, not premature completion.
- The eval layer now measures at least one real `expand_then_answer` case, not only direct-answer retrieval posture.

The remaining strategic gap is no longer “we need a runtime.” It is:

- making unknown weak slices discoverable faster through real use
- closing live archive content gaps after detection
- proving that ordinary agents can repeatedly `expand -> persist -> answer` without special tester steering
