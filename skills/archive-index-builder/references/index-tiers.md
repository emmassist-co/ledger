# Index Tiers

Use this skill to build layered indexes for large archives where full semantic enrichment is too expensive upfront.

## Tier Intent

- `L0` global coverage: one row per document plus cheap derived text and routing fields.
- `L1` local navigation: searchable blocks inside shortlisted documents.
- `L2` interpretation: claims, references, entities, evidence pointers.
- `L3` resolution: links from archive mentions to canonical parliamentary or external sources.

## Cheap-First Fields

For every document, prefer deterministic fields:

- `doc_id`
- `source_url`
- `title`
- `date`
- `legislature`
- `session`
- `document_number`
- `page_count`
- `raw_text_path`
- `summary_entries`
- `topics` when derived safely

## Expensive Fields

Delay these until promotion:

- structured claims
- normalized references
- entity linking
- canonical source resolution
- narrative summaries

## Anti-Patterns

- Embedding every page before metadata exists
- Running LLM extraction across the full archive before query demand
- Using one flat text index without legislature, date, party, or speaker filters
- Returning “resolved” answers without page or block pointers
