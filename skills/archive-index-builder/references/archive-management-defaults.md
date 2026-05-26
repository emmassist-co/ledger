# Archive Management Defaults

The skill should manage the archive proactively after initial intake.

## Goal

Make archive use feel hands-off:

- answer from current coverage when possible
- deepen coverage automatically when the next step is obvious
- build missing slices when the question clearly points to them
- ask the user only when crossing a meaningful boundary

This behavior should be governed by an explicit autonomy preference captured during intake and remembered for future use.
Stopping behavior should also be governed by a saved minimum-confidence preference captured during intake.
The archive should also persist an `operating_mode` such as `accuracy_first`, `balanced`, or `speed_first`.

## Default Loop

For each topical question:

1. query current index
2. inspect coverage and confidence
3. if enough evidence exists, answer
4. if evidence is thin but relevant material is already local, promote it
5. if evidence is still thin and adjacent source material is already discovered, expand automatically if allowed by policy
6. if evidence is still thin but the missing slice is clearly identifiable inside the agreed corpus, acquire and index that slice automatically
7. compare the resulting answer confidence against the saved minimum-confidence target
8. if still below threshold and still in-bounds, continue enriching
9. rebuild the navigation layer
10. run deterministic verifiers appropriate to the archive mode
11. answer with updated coverage and confidence

## Promotion Before Expansion

Prefer this order:

1. query promoted artifacts
2. query local but unpromoted processed material
3. promote relevant blocks or references
4. only then fetch more source material

`Not indexed yet` is not a stopping condition by itself. It means the archive should decide whether the missing slice can be built automatically.

This keeps the archive efficient and avoids unnecessary downloads.

## Auto-Expand Boundary

The skill may expand automatically when all of these are true:

- the new material is inside the agreed corpus
- the new material is adjacent to the current slice
- the new material is likely relevant to the active topic
- the expected cost is low relative to the current task

If the saved autonomy policy is `ask-first`, the skill should still stop before automatic expansion even when the technical conditions above are satisfied.

If the saved autonomy policy is `proactive`, the skill should default to automatic promotion and in-bounds slice building unless a real boundary is crossed.

If the saved autonomy policy is `hybrid`, the skill should auto-expand for local or clearly adjacent material and ask before broader slice acquisition.

If the saved minimum-confidence policy is high, the skill should be willing to do more in-bounds enrichment before stopping.

If the saved minimum-confidence policy is fast or moderate, the skill may stop earlier once the answer is responsibly supported.

If the saved `operating_mode` is:

- `accuracy_first`, require stronger verifier passes before expansion and before final answer-critical synthesis
- `balanced`, require verifier passes for provenance, policy, and answer-critical evidence
- `speed_first`, allow earlier tentative answers, but still block policy and provenance violations

The skill may also build a missing slice automatically when all of these are true:

- the question implies a clear legal/topic anchor
- the target corpus is already agreed
- the canonical source is identifiable
- the expected acquisition/promotion cost is modest
- there is no need for the user to choose among substantially different expansion paths

Examples of safe automatic expansion:

- neighboring diaries on the same listing page
- adjacent issues in the same session
- references clearly linked from already retrieved blocks
- fetching the canonical code or act needed to answer a question inside an already agreed legal corpus
- promoting the relevant article-level or block-level units needed for the answer

## Ask-First Boundary

The skill should stop and ask before expansion when:

- moving into another legislature or corpus
- the download volume is much larger than the current slice
- the source is authenticated or fragile
- the relevance is weak or speculative
- the policy set during intake said to ask first
- the archive cannot meet the saved minimum-confidence target without crossing a boundary

## Required Answer Behavior

When the archive was expanded or promoted to answer a question, say so explicitly:

- what was queried first
- what was promoted locally
- what was fetched additionally, if anything
- whether the answer comes from existing or expanded coverage
- which verifier checks passed or failed

## Anti-Patterns

- asking the user for every small expansion
- silently expanding into a much larger corpus
- reindexing the full archive for each new topic
- stopping at `not indexed yet` when the missing slice is small and clearly in-bounds
- answering from a thin slice without reporting coverage
