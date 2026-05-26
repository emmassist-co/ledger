# Parliamentary Transcript Workflow Design

**Goal:** Build an artifact-first workflow that turns one Portuguese parliamentary transcript PDF into reusable Markdown section notes, claims/reference artifacts, and multiple document-level explanation views.

**Architecture:** A deterministic Python pipeline handles Markdown-first PDF extraction, page mapping, section detection, IDs, and file writes. OpenRouter-backed LLM stages operate only on bounded intermediate artifacts such as individual sections and assembled section notes, while repo-local skills teach future agents how to run and inspect the workflow correctly.

**Tech Stack:** Python, Markdown + YAML frontmatter, OpenRouter, filesystem artifacts, pytest

## Status

Approved in conversation and frozen here before implementation.

## Problem

The system needs to process long Portuguese parliamentary transcript PDFs into durable, inspectable reading artifacts that can later support summaries, complexity-adjusted explanations, question answering, and optional external verification. The MVP should optimize for good reading notes rather than a heavy normalized political knowledge graph.

## Product Shape

The product is a single-document processing workspace, not a chat-only feature. The primary entrypoint is a local CLI command that processes one transcript PDF into a document folder under `documents/<document-id>/`.

The canonical information flow is:

```text
PDF
  -> extracted Markdown with page anchors
  -> semantic sections
  -> section notes in Markdown + frontmatter
  -> document-level claims and references
  -> document index
  -> level 1 / level 2 / level 3 views
```

Views are generated from notes and reference artifacts, never directly from the raw PDF.

## Scope

### MVP

- Markdown-first PDF parsing with plain-text fallback
- heuristic-first section detection
- parallel section note generation
- document-level claims/reference extraction
- level 1/2/3 rendered views
- filesystem output structure
- OpenRouter integration through a config-driven adapter boundary

### Prepared But Deferred

- external reference resolution as an explicit optional step
- view verification stage
- embeddings or database indexing
- cross-document analytics
- UI

## Repository Structure

```text
skills/
  process-parliamentary-transcript/
  pdf-parser/
  section-detector/
  section-note-writer/
  claims-and-references-extractor/
  complexity-slider-renderer/
  external-reference-resolver/
  view-verifier/

src/parliament/
  cli.py
  config.py
  models/
  pipeline/
  extract/
  sectioning/
  llm/
  render/
  io/

prompts/
  section-note.md
  claims.md
  level-1.md
  level-2.md
  level-3.md
  verifier.md

config/
  models.example.yaml
  pipeline.example.yaml

tests/
  fixtures/
  unit/
  integration/

documents/
  DAR-I-087/
```

## Component Boundaries

- `models/` defines typed contracts for documents, sections, claims, references, and run metadata.
- `extract/` contains deterministic PDF-to-Markdown extraction and page mapping.
- `sectioning/` contains deterministic heuristics, normalization, and section classification logic.
- `pipeline/stages/` coordinates work but does not bury prompt text or parsing logic.
- `llm/` exposes task-level methods such as `write_section_note()` and `render_view()`, with OpenRouter as the first concrete transport.
- `prompts/` stores versioned prompt templates instead of scattering prompts inline.
- `skills/` provides operational guidance for agents and transcript-specific judgment rules; it does not duplicate code.

## Artifact Model

Each processed document produces this shape:

```text
documents/DAR-I-087/
  source/
    DAR-I-087.pdf
    extracted_text.md
    page_map.json

  sections/
    00-session-summary.md
    01-ukraine-solemn-session.md
    ...

  references/
    claims-to-check.md
    external-references.md
    fetched-sources.md

  views/
    level-1-simple.md
    level-2-standard.md
    level-3-detailed.md

  index.md
  metadata.json
```

### Source Artifacts

- `extracted_text.md` is the canonical extraction artifact.
- It preserves page markers, speaker turns, procedural notes, and useful structure in Markdown form.
- `page_map.json` maps extracted blocks and page anchors back to source pages. The MVP does not require character-perfect offsets if page-level grounding is reliable.

### Section Artifacts

Each section note is the primary durable reading artifact and must include:

- YAML frontmatter with document ID, section ID, title, type, page range, topics, actors, parties, importance, references, and related sections
- body sections that distinguish:
  - transcript-established facts
  - speaker claims
  - cautious interpretation
- evidence pointers back to transcript pages

### Reference Artifacts

- `claims-to-check.md` contains normalized claims worth external verification.
- `external-references.md` contains deduplicated external concepts or sources worth resolving later.
- `fetched-sources.md` is always present as a stable target, even when resolution has not run.

### View Artifacts

- `level-1-simple.md` targets a casual reader.
- `level-2-standard.md` targets an informed citizen or journalist.
- `level-3-detailed.md` targets an analyst or researcher.

All three views must be based on the same underlying notes and reference artifacts.

### Operational Metadata

`metadata.json` records run provenance such as:

- document ID
- title and language
- page count
- pipeline version
- prompt versions
- model configuration used
- timestamps
- resolver and verifier status

## Language Policy

- Content artifacts are Portuguese-first.
- Frontmatter keys and machine-readable JSON use English keys.
- English outputs can be added later as separate rendered views instead of replacing the canonical Portuguese artifacts.

## Workflow

The initial processing DAG is:

```text
parse_pdf
  -> detect_sections
  -> write_section_notes (parallel per section)
  -> extract_claims_and_references
  -> write_index
  -> render_views (parallel for levels 1/2/3)
```

Prepared but deferred stages:

```text
resolve_external_references
verify_views
```

## Stage Responsibilities

### 1. `parse_pdf`

- extract Markdown-first text from the PDF with page anchors
- preserve procedural content, votes, interruptions, speaker names, party abbreviations, and opening/closing material
- use a Markdown-preserving extraction tool such as `pymupdf4llm` when possible
- fall back to plainer extraction only when Markdown conversion quality is poor

### 2. `detect_sections`

- use transcript-specific heuristics rather than arbitrary token chunking
- look for cues such as session summaries, solemn session openings, vote blocks, declarations, response blocks, and closing notes
- produce stable section IDs and titles
- preserve uncertainty when boundaries are weak

### 3. `write_section_notes`

- run one LLM task per section
- feed only bounded section text plus metadata
- require fact/claim/interpretation separation
- include evidence pointers and external reference hints

### 4. `extract_claims_and_references`

- normalize claims that are statistical, legal, historical, programmatic, or otherwise disputable
- deduplicate external references across the document
- avoid extracting generic rhetorical attacks as if they were claims worth checking

### 5. `write_index`

- create the top-level human entrypoint for the document
- summarize main sections, conflicts, decisions, and unresolved checks
- link to generated views

### 6. `render_views`

- generate level 1/2/3 explanations from section notes, claims, and fetched references only
- forbid new facts or silent claim inflation
- keep the same underlying meaning across all three levels

### 7. `resolve_external_references` (deferred)

- run only after references are deduplicated at document level
- prefer official, parliamentary, EU, OECD, or otherwise authoritative sources
- write normalized source summaries and usage notes to `fetched-sources.md`

### 8. `verify_views` (deferred)

- compare rendered views against section notes and reference artifacts
- detect unsupported facts, overstated claims, missed major events, and incorrect verification framing

## Heuristic vs LLM Split

Use deterministic code when the task affects structure, provenance, IDs, file layout, or reproducibility. Use the LLM when the task is to transform already-bounded source material into readable notes or explanations. When deterministic heuristics are uncertain, record the uncertainty rather than hiding it with confident prose.

## OpenRouter Integration

The system uses a provider-agnostic task boundary with OpenRouter as the first concrete adapter.

Recommended configuration behavior:

- config-first model selection
- CLI override support for experimentation
- artifact provenance records the model used for each LLM-backed stage

The code should treat OpenRouter as one concrete transport, even though it can route to multiple upstream models.

## Repo-Local Skill Design

### Top-Level Skill

`process-parliamentary-transcript` is the main operator skill. It tells future agents to:

- process the transcript through the full artifact chain
- inspect outputs in order
- avoid summarizing directly from the PDF
- treat section notes as the canonical intermediate representation

### Sub-Skills

- `pdf-parser`: extraction rules, preservation constraints, fallback behavior
- `section-detector`: parliamentary transcript segmentation cues
- `section-note-writer`: fact/claim/interpretation discipline
- `claims-and-references-extractor`: what counts as a check-worthy claim
- `complexity-slider-renderer`: same-information rendering across levels
- `external-reference-resolver`: source priority and deduped resolution
- `view-verifier`: groundedness and overstatement checks

These skills exist to guide agent behavior and inspection order, not to replace executable code.

## Testing Strategy

### Unit Tests

- extraction normalization
- page mapping
- section heuristics
- slug and section ID generation
- claims/reference deduping
- file output layout

### Integration Tests

- one small representative transcript excerpt fixture
- one larger DAR fixture when practical
- assertions on generated artifact structure and key metadata

### LLM Contract Tests

- mocked or recorded OpenRouter responses for note writing and rendering
- validation of frontmatter shape, output contracts, and provenance metadata

### Golden Artifact Tests

- expected note and view outputs for stable fixtures
- useful because the product is artifact-first and human-readable

## Risks and Guardrails

- messy extraction can poison every downstream step, so extraction artifacts must stay easy to inspect
- over-aggressive section splitting can destroy political coherence
- note generation must never collapse claims into facts
- views must never bypass the notes and read raw PDF text directly
- external browsing must stay centralized and explicit

## Suggested First Implementation Slice

1. Scaffold the Python package, CLI, config files, and repo-local skill folders.
2. Implement Markdown-first PDF extraction with fallback and file output.
3. Implement heuristic section detection and stable section IDs.
4. Implement OpenRouter-backed section note generation.
5. Implement claims/reference aggregation.
6. Implement level 1/2/3 rendering from notes only.
7. Add fixture-backed tests for one representative document flow.

## Out of Scope For The First Build

- graph database storage
- deep verification and autonomous browsing
- UI and user accounts
- cross-document comparisons
- political ontology modeling beyond what the artifacts naturally capture

## Implementation Handoff

This document is the approved design baseline. The next step is to create a task-by-task implementation plan and only then begin coding.
