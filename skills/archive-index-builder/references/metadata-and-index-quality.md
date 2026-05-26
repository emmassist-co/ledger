# Metadata And Index Quality

Use disciplined metadata practices so the archive stays queryable, auditable, and rebuildable.

## Core Rule

Separate what the source explicitly says from what the agent infers.

## Metadata Classes

Keep two classes of fields:

- `observed_*`: directly visible in source material
- `normalized_*` or inferred fields: cleaned, mapped, or guessed values

Examples:

- `source_title`
- `source_date_text`
- `source_document_id`
- `normalized_date`
- `normalized_doc_id`
- `inferred_topics`

Do not silently replace raw values with normalized ones.

## Deterministic First

Prefer deterministic extraction before LLM inference:

- HTML labels and selectors
- URL parameters
- filenames
- visible headings
- PDF metadata
- stable source identifiers

Use LLM inference only when the source does not expose the field cleanly.

For corpus text itself, prefer deterministic extraction over paraphrase. If the archive needs human-readable summaries, store them as a separate derived field or artifact.

## Stable IDs

Artifact and document ids should be stable across rebuilds.

Prefer:

- source system ids
- document numbers
- legislature/session plus issue number
- deterministic slugs built from stable source metadata

Avoid ids derived from summaries or other changing text.

## Schema Versioning

Keep version and method fields so the archive can evolve safely:

- `schema_version`
- `extraction_method`
- `extracted_at`

## Confidence

Use confidence only for inferred fields:

- topic tags
- corpus classification
- entity linking
- reference resolution

Do not attach fake confidence to explicit source facts such as visible dates or titles.

## Field Provenance

For important metadata, record where it came from when feasible:

- `html`
- `url`
- `filename`
- `pdf_heading`
- `agent_inference`

This can be a per-field map or a simpler `metadata_sources` block.

For high-stakes corpora, also preserve:

- `source_local_path`
- `source_hash`
- `source_version` or consolidation/effective date when relevant
- `verbatim_status`
- `extract_pointer` such as article number, anchor id, heading path, or page span

## Validation Checklist

Before writing or updating artifacts and index entries, check:

- required fields are present
- ids are unique and stable
- dates are parseable or explicitly unknown
- source URLs are preserved
- page ranges are sensible
- linked ids resolve or are marked pending
- raw and normalized fields are not conflated

## Navigation Index Discipline

The navigation index should be:

- compact
- rebuildable
- derived from artifacts plus deterministic metadata
- not manually edited as a primary source

For large corpora, the index should also separate:

- routing metadata
- source provenance
- extract-level units
- derived summaries or notes

Do not force all retrieval quality onto one flat `search_text` field if the corpus is expected to grow large.

Its job is to locate candidate artifacts quickly, not to replace the artifacts.

## Over-Tagging Warning

Do not add many weak topic tags early.

Prefer:

- a few strong source-derived tags
- conservative inferred topics
- deeper enrichment only after repeated use
