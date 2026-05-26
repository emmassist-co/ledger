# Query And Promotion

## Query Cascade

1. Filter by metadata first.
2. Prefer extract-level and verbatim units over summaries when they exist.
3. Run keyword search over summaries or block text.
4. Rerank a small candidate set.
5. Open only the top candidate blocks.
6. Promote documents or blocks that recur.

## Promotion Triggers

Promote a document from `L0` to `L1` when:

- the same topic hits it repeatedly
- a user asks a concrete reference question
- summaries point to a narrow debate block

Promote from `L1` to `L2` when:

- the same block is reused
- the answer depends on claims, references, or entity normalization
- the archive item becomes part of a high-value topic cluster

Promote to `L3` only when:

- the question depends on a canonical law, vote, initiative, or external report
- the answer would otherwise remain ambiguous

For legal or regulatory corpora, promote to extract-level artifacts before writing interpretive notes whenever the answer depends on exact wording.

## Query Contract

Every query response should try to return:

- matched document ids
- matched block ids if available
- why the match was selected
- evidence pointers
- confidence
- next hop if canonical resolution is still needed

When exact wording matters, include which extract artifact or raw-source pointer carried the decisive evidence.
