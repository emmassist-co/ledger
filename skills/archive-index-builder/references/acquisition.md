# Acquisition

Prefer acquisition paths that produce clean local Markdown while keeping provenance intact.

For high-stakes corpora, optimize first for auditability and replayability, not convenience.

## First Preference

For archive enrichment, prefer the archive's canonical official sources first.

For public web pages, prefer `markdown.new` in the first version of the workflow when you need to acquire a seed listing, landing page, or other non-canonical navigation surface.

When the source family has an official listing or feed, the first durable step should usually be:

1. sync the canonical listing into registry-level artifacts
2. keep direct document URLs and observed listing metadata
3. ingest only the selected documents into local raw source plus retrieval indexes

This keeps recency cheap without forcing full eager ingestion.

Use it for:

- single landing pages
- public listings and archive indexes
- bounded site crawls
- public PDF-to-Markdown conversion when useful

Repo helper:

- `uv run ledger archive fetch-url --root <archive-root> --source-id <id> --url <public-url>`
- this uses `markdown.new` first and falls back to `r.jina.ai`, then appends a manifest row under `source/manifests/downloads.jsonl`
- if both clean capture paths fail, treat browser automation as the last resort rather than falling back to raw `curl` HTML capture

## Why

- reduces custom crawler code
- yields agent-friendly Markdown quickly
- works well with a Markdown-first artifact strategy
- avoids wasting tokens on scripts, menus, banners, and other page chrome

## Canonical-First Rule

When answering questions through an archive:

1. query the local archive first
2. identify the canonical official source for the missing slice
3. acquire that source and persist it back into the archive
4. answer from the enriched archive
5. use broader web search only if the archive plus canonical-source path is insufficient

Do not default to generic web search when the official canonical source is identifiable.

## Source Preservation Rule

Do not treat a fetched summary or converted Markdown page as the ultimate source when the canonical document itself is obtainable.

When feasible, save:

- the official HTML, PDF, XML, or equivalent source artifact
- fetch timestamp
- response headers or other acquisition metadata when useful
- content hash
- parent discovery URL
- local storage path

This preserved source should be enough to rebuild downstream extract artifacts later.

## Local Persistence Rule

Never rely on the remote service as the archive.

Always persist locally:

- fetched Markdown
- raw official source files
- original source URL
- source parent URL
- acquisition timestamp
- content hash
- local file path

## Fallbacks

Use direct downloads or existing local scripts when:

- access is authenticated
- the page is not converted reliably
- the corpus already has a stable local parser
- the source format is easier to process locally than through the service
- the canonical official source should be captured directly rather than through a generic search flow

For public websites, prefer this fallback order:

1. canonical official document download when available
2. `markdown.new` capture
3. `r.jina.ai` or an equivalent clean text/Markdown conversion
4. local section or page index search over the captured Markdown
5. agent browser only when the page genuinely requires rendering or interaction

Do not default to raw HTML capture for model-facing retrieval. If raw HTML is saved for auditability, keep it separate from the text the model actually reads.

For PDFs that will be revisited repeatedly, do not stop at saving the raw file. Build a local page-level extraction and search index with `liteparse` so later questions can open only the relevant pages instead of re-reading the whole document.

- `uv run ledger archive index-pdf --root <archive-root> --source-id <id> --pdf-path <local-pdf>`
- `uv run ledger archive search-pdf --root <archive-root> --query \"...\" [--source-id <id>]`
- persist both the extracted page markdown and the raw `liteparse` JSON so later block/bbox navigation does not require reparsing the PDF

## Deterministic Extraction Rule

After acquisition, prefer deterministic local extraction before any LLM synthesis:

- split statutes or codes into article or section units
- split debate records into agenda items, interventions, or page-bounded blocks
- keep exact pointers to pages, headings, anchors, or article numbers
- write summaries only after the extract layer exists
