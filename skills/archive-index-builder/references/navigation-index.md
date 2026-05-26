# Navigation Index

The navigation index exists so an agent can find the right artifacts quickly without scanning the whole archive.

## Purpose

Return a small, ranked set of candidate artifacts and links:

- which files to open
- why they matched
- which linked artifacts to follow next

## Source Of Truth

- Artifacts in Markdown remain the source of truth.
- The navigation index is a cache and locator.
- It must be rebuildable from artifacts plus deterministic metadata.

## Minimum Fields

Each index entry should capture:

- `artifact_id`
- `artifact_type`
- `path`
- `title`
- `date`
- `corpus`
- `topics`
- `speaker`
- `party`
- `linked_ids`
- `search_text`
- `tier`

## Query Contract

A good query response should return:

- top candidate artifact ids
- file paths
- match reasons
- linked ids to follow next
- confidence or score

## Recommended Build Strategy

- store a compact SQLite or JSONL navigation layer
- rebuild it from Markdown artifacts after each indexing run
- prefer metadata filters before semantic or fuzzy matching
