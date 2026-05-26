# Source And Expansion

The index should be able to grow over time without losing provenance.

## Source Chain

Every indexed artifact should be traceable back through the discovery chain:

- seed page
- parent listing or navigation page when applicable
- canonical source document URL
- local downloaded file
- extracted block or derived artifact

## Required Provenance Fields

Keep these whenever possible:

- `source_url`
- `source_parent_url`
- `source_system`
- `source_document_id`
- `discovered_at`
- `downloaded_at`
- `local_file`
- `page_start`
- `page_end`

## Discovery States

Distinguish what the system knows from what it has processed.

- `discovered`: visible from source navigation but not downloaded
- `download_queued`: selected for download
- `downloaded`: file exists locally
- `indexed_l0`: registry/index entry exists
- `indexed_l1`: block artifacts exist
- `enriched_l2`: claims/references/entities exist
- `resolved_l3`: canonical links or final resolution artifacts exist

## Expansion Model

The system should not eagerly download everything.

Instead:

1. download and index the agreed seed slice
2. record adjacent candidates discovered during navigation
3. answer from current coverage when possible
4. if the answer is thin or ambiguous, offer expansion into undiscovered or undownloaded nearby material

## Adjacent Candidates

Examples:

- neighboring issues on an index page
- other sessions in the same legislature
- linked acts or reports referenced by a retrieved artifact
- nearby editions, articles, or debate blocks exposed by the source navigation

## Agent Behavior

When coverage is insufficient, prefer:

- "I found likely adjacent source documents not yet downloaded"
- "I can expand the index into these next"

Do not pretend the current indexed slice is the whole corpus.
