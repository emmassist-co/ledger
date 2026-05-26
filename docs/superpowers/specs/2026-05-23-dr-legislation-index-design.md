# DR Legislation Index Design

## Goal

Build a real `Diário da República` corpus inside the existing archive instance at `/Users/alexandre/dev/parliament/archive-index` so the archive can:

- discover legislation broadly enough to know what exists,
- answer precise legal questions in at least one deep vertical,
- connect parliamentary debate references from `DAR` to canonical `DR` legislation,
- grow safely over time without mixing instance-specific archive behavior into the generic indexing skill.

This is an archive-instance feature, not a generic-skill change.

## Why This Exists

The archive currently has:

- a useful `DAR` debate corpus,
- a narrow `DR` bridge around `Agenda do Trabalho Digno`,
- no real legislation index broad enough to answer general legal questions.

That means the archive can connect some labour debates to canonical legislation, but it cannot yet answer broader law questions such as corporate capital gains treatment from archive-backed coverage.

The missing capability is a real `DR` corpus with:

- broad shallow discoverability,
- one deep vertical with article-level legal anchors,
- explicit cross-corpus links back to the `DAR` side.

## Scope

### In scope

- Add a `DR` corpus under the existing archive instance
- Build a recent-window outer map from `legislacao-por-data`
- Record visible `theme` / `code` memberships as expansion facets
- Build a deep tax vertical
- Use `IRC` as the first canonical tax anchor
- Promote legal answering units to `article_block + consolidation_note`
- Keep the shared navigation graph across `DAR` and `DR`

### Out of scope

- Rewriting the generic `archive-index-builder` skill
- Full historical mirroring of all `DR`
- Exhaustive legal coverage across all domains
- Automatic crawling outside the approved recent window

## Core Design

### Two-layer corpus

The `DR` index has two layers from day one.

#### 1. Outer map

Purpose:

- broad discoverability,
- future expansion into other legal domains,
- coverage accounting.

Characteristics:

- sourced primarily from `legislacao-por-data`,
- recent window only for the first build,
- one shallow registry artifact per discovered act,
- visible `theme` and `code` memberships recorded as facets,
- canonical act page stored as truth.

#### 2. Deep vertical

Purpose:

- make the archive answer real legal questions now,
- prove article-level legal retrieval,
- establish the promotion model for future legal domains.

Characteristics:

- first deep vertical is tax law,
- first canonical anchor is `IRC`,
- related tax acts can be pulled in automatically inside policy,
- answering unit is `article_block + consolidation_note`.

## Source Strategy

### Discovery surface

Primary discovery starts from:

- `https://diariodarepublica.pt/dr/legislacao-por-data`

Reason:

- best base for broad coverage and refresh,
- least opinionated browse path,
- appropriate for building a real archive map instead of a topic-only slice.

### Canonical truth

Canonical truth lives on the act detail pages and consolidated law pages, not on browse pages.

That means:

- `por data` is used to discover,
- act pages are used to normalize,
- consolidated views are used to understand current operative text when relevant,
- `por tema` and `por código` are treated as facets, not as ingestion roots.

## Archive Structure

Add `DR` as a peer corpus inside the existing archive instance:

```text
/Users/alexandre/dev/parliament/archive-index/
  artifacts/
    dr/
      registry/
      acts/
      article-blocks/
      consolidation-notes/
      relations/
      facets/
    dar/
      ...
  source/
    dr/
      crawls/
      raw/
  index/
    navigation.sqlite
    documents.jsonl
    links.jsonl
```

Notes:

- The archive remains one graph.
- `DAR` and `DR` are separate corpora within that graph.
- The shared navigation layer is rebuilt from artifacts, not hand-maintained.

## Artifact Types

### `registry`

Purpose:

- shallow record of a discovered `DR` act,
- broad coverage,
- initial navigation target.

Expected fields:

- `artifact_id`
- `artifact_type`
- `schema_version`
- `extraction_method`
- `extracted_at`
- `doc_id`
- `source_system`
- `source_url`
- `source_parent_url`
- `source_document_id`
- `source_title`
- `source_date_text`
- `normalized_date`
- `normalized_type`
- `discovery_state`
- `discovered_at`
- `confidence`
- `linked_ids`
- visible `theme` / `code` facet fields when observed

### `act`

Purpose:

- canonical promoted law/decree artifact for a high-value act,
- richer legal metadata and cross-links than a registry entry.

Typical examples:

- `Código do IRC`
- major amending laws relevant to corporate taxation

### `article_block`

Purpose:

- exact legal provision or section used for answering.

This is the required unit for precise tax questions. A question like “how are company capital gains taxed?” should resolve here when the archive is mature enough.

### `consolidation_note`

Purpose:

- short operative synthesis when the answer depends on multiple provisions, amendments, or a consolidated view.

This keeps the archive from forcing the agent to improvise legal synthesis on every query.

### `relation`

Purpose:

- explicit graph edges between acts and other legal artifacts.

Examples:

- `amends`
- `rectifies`
- `regulates`
- `consolidates`
- `related_tax_cluster`

### `facet`

Purpose:

- store browse memberships that support future expansion.

Examples:

- code membership,
- theme membership,
- other observed public categorizations from the `DR` site.

## Tax Vertical

### Why tax first

Tax is the hardest useful test because it forces:

- precise legal anchors,
- current operative reading,
- cross-act navigation,
- disciplined confidence reporting.

If the archive can answer tax questions well, the legal indexing model is probably sound.

### First anchor

Start from `IRC`, then expand to related acts discovered during indexing.

The archive should not assume one statute answers everything. Nearby acts can be pulled into the deep slice when they are:

- clearly related,
- inside the approved recent window,
- needed to answer the active tax question.

### Answering unit

Default legal answer path:

1. locate canonical act,
2. locate relevant `article_block`,
3. read or create `consolidation_note` if multiple amendments or provisions matter,
4. answer with provenance and confidence.

## Growth Policy

### Default behavior

The archive should manage itself within policy:

- query current coverage first,
- promote local material before fetching more,
- auto-expand inside the recent `DR` window for clearly related tax material,
- ask only when expansion crosses that boundary or moves into a different legal area.

### Boundary crossing

The system should stop and ask when it needs to:

- go outside the recent `DR` window,
- enter a new legal domain beyond the active vertical,
- perform broader crawling than the agreed outer-map policy.

## Coverage and Confidence

Legal answers must inherit the same coverage contract already emerging on the `DAR` side.

Every legal answer should be able to report:

- searched scope,
- whether the answer came from act-level or article-level coverage,
- whether a consolidation note was available,
- what nearby related acts were considered,
- answer confidence,
- slice confidence,
- corpus confidence,
- whether expansion is recommended.

The archive must not bluff absence or precision it does not have.

## Cross-corpus Linking

The archive must treat `DAR` and `DR` as connected corpora.

Required link patterns:

- `dar:reference -> dr:act`
- `dar:resolution -> dr:consolidation_note`
- `dr:act -> dr:article_block`
- `dr:act -> dr:relation -> dr:act`

This lets political questions move into canonical law and lets legal questions recover debate context when useful.

## Operational Flow

### Outer-map flow

1. Crawl recent `por data` listings
2. Discover candidate acts
3. Write `registry` artifacts
4. Record observed `theme` / `code` facets
5. Rebuild shared navigation index

### Deep-tax flow

1. Start from `IRC`
2. Promote canonical tax acts
3. Extract relevant `article_block` artifacts
4. Write `consolidation_note` artifacts where operative answers span multiple provisions
5. Add relation edges to nearby tax acts
6. Rebuild shared navigation index

### Query flow

1. Query shared index
2. Navigate to `DR` registry/act/article artifacts
3. Expand inside policy if coverage is insufficient
4. Answer from `article_block + consolidation_note` when possible

## Risks

### 1. Overbuilding the crawler before proving the archive

Mitigation:

- keep first build recent-window only,
- keep browse discovery simple,
- prioritize artifact-writing and navigation over crawler cleverness.

### 2. Tax answers becoming too hand-wavy

Mitigation:

- require article-level anchors for precise answers,
- use consolidation notes when amendment history matters,
- report scope and confidence explicitly.

### 3. Mixing generic skill behavior with archive-instance specifics

Mitigation:

- keep this design scoped to `/archive-index`,
- do not encode `DR` archive specifics into the generic skill during this implementation.

## Success Criteria

The design is successful when:

- the archive has recent broad `DR` registry coverage,
- the archive knows observed theme/code pathways for future expansion,
- the archive has a deep tax slice anchored on `IRC`,
- the navigation graph connects `DAR` and `DR`,
- a tax question can resolve to article-level legal material with a clear confidence report,
- expansion inside the approved policy works without manual archive babysitting.
