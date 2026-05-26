# Acquisition

Prefer acquisition paths that produce clean local Markdown while keeping provenance intact.

For high-stakes corpora, optimize first for auditability and replayability, not convenience.

## First Preference

For archive enrichment, prefer the archive's canonical official sources first.

For public web pages, prefer `markdown.new` in the first version of the workflow when you need to acquire a seed listing, landing page, or other non-canonical navigation surface.

Use it for:

- single landing pages
- public listings and archive indexes
- bounded site crawls
- public PDF-to-Markdown conversion when useful

## Why

- reduces custom crawler code
- yields agent-friendly Markdown quickly
- works well with a Markdown-first artifact strategy

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

## Deterministic Extraction Rule

After acquisition, prefer deterministic local extraction before any LLM synthesis:

- split statutes or codes into article or section units
- split debate records into agenda items, interventions, or page-bounded blocks
- keep exact pointers to pages, headings, anchors, or article numbers
- write summaries only after the extract layer exists
