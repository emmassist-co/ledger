# Question-Driven Enrichment

The archive should improve through use.

## Core Rule

A user question is both:

- a retrieval request
- a candidate trigger for archive enrichment

The skill should not treat `missing from current index` as the final outcome when the missing slice can be built safely.

Whether the skill should do that proactively or ask first must be captured during intake as an autonomy preference and persisted in the archive policy/config.
The archive should also persist a minimum-confidence target that determines when enrichment can stop.
The archive should also persist an `operating_mode` that controls how strict the verifier gates are.

## Default Runtime Loop

For each substantive question:

1. identify the likely domain, corpus, and retrieval unit
2. query the current archive
3. assess coverage and confidence
4. if current coverage is enough, answer
5. if current coverage is thin, promote local material
6. if still thin, expand into adjacent discovered material
7. if still thin but the needed slice is clearly identifiable and in-bounds, acquire and index that slice from canonical official sources
8. compare answer confidence to the saved minimum-confidence target
9. if the answer is still below threshold and further in-bounds enrichment is available, continue
10. rebuild the navigation layer
11. run deterministic verifiers for coverage, provenance, policy, and claim support as needed
12. answer from the enriched archive

Generic web search should be fallback only after the local archive and canonical-source path have both been tried or shown insufficient.

## In-Bounds Enrichment

Enrichment should happen automatically when:

- the user already agreed the corpus or archive boundary
- the needed source is canonical or easy to identify
- the enrichment is proportional to the question
- the cost is small relative to the task
- the saved autonomy policy permits proactive enrichment
- the expected next enrichment step is useful for reaching the saved minimum-confidence target

Examples:

- a labour-law question triggers promotion of a specific code/article slice already linked from debate artifacts
- an IRS reinvestment question triggers acquisition of the relevant CIRS articles and a consolidation note
- a debate-reference question triggers fetching the linked act or neighboring issue

## Ask-First Cases

Stop and ask only when:

- the question could route into multiple large corpora
- the next step would cause a large crawl or long-running ingest
- the canonical source is ambiguous enough that user intent matters
- the source is authenticated, fragile, or high-cost
- the saved autonomy policy is `ask-first`, or the situation exceeds what `hybrid` allows
- the saved minimum-confidence target cannot be met without crossing a boundary

## Required Answer Behavior

If enrichment happened during the answering process, say so explicitly:

- what existed already
- what was promoted
- what was fetched or indexed
- what remains incomplete
- which verifier results supported the stop/expand decision

## Anti-Pattern

Do not answer archive questions like this:

- `the archive does not have that yet`

Prefer:

- `current coverage was insufficient, so I expanded the archive into the relevant slice and answered from that`

or, when blocked:

- `current coverage is insufficient and the next expansion crosses the agreed boundary, so I need your approval before continuing`
