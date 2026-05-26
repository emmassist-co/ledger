# Intake Questions

Use adaptive intake after source inspection, not before.

## Core Questions

Ask these first:

1. What questions should this index answer well?
2. Where should the archive workspace live?
3. What retrieval unit should the index optimize for?
4. Should this archive optimize for `accuracy_first`, `balanced`, or `speed_first`?
5. What provenance should answers return?
6. Should the archive proactively enrich missing slices while answering, or ask first before expanding?
7. What minimum confidence should answers aim for before the archive stops enriching?

## Follow-Up Questions

Ask only when the source inspection leaves ambiguity:

- Should the first pass stop at registry entries or create block artifacts too?
- Should the index link to canonical external sources such as laws, votes, or reports?
- Which metadata should be queryable: date, speaker, party, topic, issue number, institution?
- Should the build cover only the visible slice of the corpus or recursively discover adjacent slices?
- How should updates work: one-off build, manual refresh, or recurring refresh?
- What autonomy policy should govern future question-driven enrichment: `proactive`, `hybrid`, or `ask-first`?
- What minimum confidence policy should govern stopping: `fast/medium/high/very-high` or an equivalent threshold?
- Should deterministic verifiers be required before expansion and before final answer synthesis?

## Session-Like Example

If the seed page exposes legislature and session selectors, ask:

- should the first build stay within the current legislature/session or enumerate all visible ones?
- should the index optimize for diary-level retrieval or debate-block retrieval?
- should references stop at parliamentary artifacts or link onward to canonical legal texts?

## Legal-Gazette Example

If the seed page looks like a legal publication archive, ask:

- should the retrieval unit be act, article, amendment block, or issue?
- should the skill recommend `accuracy_first` and require canonical-source plus extract-level verification?
- should the index resolve amendment chains immediately or defer them?
- should canonical authority come from the gazette itself or a linked legal consolidation source?
