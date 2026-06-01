---
name: canonical-source-explorer
description: Use when a new canonical source family needs cheap-first exploration, source-shape diagnosis, and a generated acquisition posture before domain-pack or archive scaffolding locks in source rules
---

# Canonical Source Explorer

Explore canonical sources as source families, not as arbitrary websites.

## Purpose

This skill exists to answer:

- what kind of canonical source surface is this?
- what is the cheapest trustworthy fetch path?
- which acquisition posture should the generated archive use?
- what helper surfaces should Ledger scaffold for later operators?

The goal is not to turn every site into an API wrapper.
The goal is to compile source-shape knowledge into the archive contract.

## Rules

- Prefer cheap deterministic probes before browser steps.
- Separate discovery evidence from archive evidence.
- Treat app shells, JS bundles, menus, and static assets as exploration clues, not as archive sources.
- Prefer feed, detail-page, and raw-file surfaces over browser-only flows when they exist.
- Only promote a source surface into pack rules when it is canonical, stable enough, and replayable.
- Output recommendations that can be consumed by `domain-archive-pack-builder` and `archive-index-builder`, not freeform browsing notes.
- Use browser capture only when cheap probing cannot reveal a viable canonical path.
- A discovered hidden API is still only an acquisition helper; Ledger remains the judge of persistence, support, and answer posture.

## Workflow

1. Start from one or more seed URLs for the source family.
2. Run the deterministic probe helper on each seed:
   - `uv run python skills/canonical-source-explorer/scripts/probe_source_family.py <url>`
3. Classify each seed into a source shape such as:
   - `rss_feed`
   - `direct_pdf`
   - `canonical_detail_page`
   - `consolidated_legal_view`
   - `listing_page`
   - `app_shell`
   - `structured_xml`
4. Record the recommended acquisition posture for that family.
5. Decide whether the source family should stay:
   - `native` to Ledger
   - `browser-assisted`
   - `future adapter candidate`
6. Translate the result into archive-local contract surfaces:
   - `recipes/source-families.yaml`
   - `recipes/source-playbooks.yaml`
   - `recipes/source-acquisition.yaml`
   - helper script expectations under `scripts/`
7. Only after the source family is understood, let the archive builder or domain-pack builder lock in rules.

## Outputs

The skill should produce or update:

- a compact exploration report for the family
- source-family shape classification
- recommended acquisition posture
- recommended retrieval unit
- browser-escalation bar
- candidate helper surfaces to scaffold later

Good helper surfaces include:

- `sync_source_registry.py`
- `ingest_source_document.py`
- `probe_source_family.py`
- source-family-specific thin wrappers over those generic helpers

## What To Learn From Printing Press

The useful upstream lessons are:

- reachability ladders before expensive exploration
- capture vs analysis separation
- explicit noise filtering
- minimum-sample and replayability thinking
- discovery artifacts that later steps can audit

Do not copy:

- turning shell assets into fake API endpoints
- treating docs-to-spec LLM output as sufficient source truth
- assuming every source should end as a wrapper CLI

## Integration

Use this skill before or during:

- `archive-index-builder` when the source family is unfamiliar
- `domain-archive-pack-builder` when the pack still needs source-shape rules

Read [references/exploration-principles.md](references/exploration-principles.md) before broad exploration.
Read [references/integration-points.md](references/integration-points.md) before deciding where the result belongs in Ledger.
