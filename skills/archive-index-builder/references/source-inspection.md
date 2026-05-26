# Source Inspection

Inspect the seed source before asking setup questions when the user provides a URL.

## Goal

Infer enough about the corpus to ask better intake questions:

- corpus family
- navigation pattern
- likely canonical units
- likely retrieval unit
- likely metadata fields

## What To Look For

- page title and section headers
- selectors for year, legislature, session, category, or edition
- repeated link patterns
- file endpoints such as PDF or HTML detail pages
- stable ids in query params, filenames, or slugs
- clues about hierarchy such as `series`, `session`, `issue`, `act`, or `article`

## Output Of Inspection

Produce a short working hypothesis before intake:

- likely corpus type
- likely canonical document type
- likely retrieval unit
- open ambiguities that need user input

Example:

- corpus: parliamentary diaries
- canonical document: session diary PDF
- retrieval unit: debate block or intervention
- ambiguities: whether to index only one legislature or all visible legislatures, and whether to link to canonical legal sources

## Anti-Patterns

- asking generic archive questions before reading the page
- assuming the landing page is itself the canonical corpus unit
- beginning a full crawl before clarifying scope
