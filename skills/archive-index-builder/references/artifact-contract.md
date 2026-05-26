# Artifact Contract

Write archive artifacts as Markdown with frontmatter whenever the agent may need to read them directly.

## Canonical Artifact Rule

- Markdown artifacts are the primary agent-facing corpus.
- The navigation index is a secondary locator layer.
- Raw downloads and deterministic extracts remain the ultimate audit layer.
- Agent-facing reasoning should prefer deterministic extract artifacts over summaries whenever the answer turns on exact wording.
- LLM-authored summaries, crosswalks, and resolutions are derived layers, never the only surviving canonical representation.

## Required Artifact Families

- `source`: raw downloaded source files plus manifests
- `registry`: one artifact per source document
- `extracts`: verbatim or deterministically extracted article, section, page, or block units
- `blocks`: one artifact per retrieval unit inside a document
- `claims`: promoted extracted claims when needed
- `references`: promoted reference candidates when needed
- `entities`: normalized canonical entities when needed
- `resolutions`: final answer-oriented cross-artifact notes when needed

## Minimum Frontmatter

Every artifact should include enough fields for later navigation:

- `artifact_type`
- `artifact_id`
- `source_url` or `doc_id`
- `source_local_path` when a raw file is retained
- `source_hash` when feasible
- `path` only if generated elsewhere
- `published_on` when known
- `page_start` and `page_end` when applicable
- `verbatim_status` such as `verbatim`, `deterministic_extract`, or `summary`
- `linked_ids`
- `confidence` when interpretation is involved

## Registry Example

```md
---
artifact_type: registry
artifact_id: reg-session-087
doc_id: SESSION-087
title: Session Log 087
source_url: https://official.example.org/session/087.pdf
published_on: 2026-05-07
source_family: session-log
edition: 87
topics:
  - labor reform
---
```

## Block Example

```md
---
artifact_type: block
artifact_id: blk-session-087-017
doc_id: SESSION-087
speaker: Speaker Name
affiliation: Coalition A
page_start: 19
page_end: 19
linked_ids:
  - ref-core-policy
---
```

## Extract Example

```md
---
artifact_type: extract
artifact_id: ext-cirs-43
doc_id: CODE-43
source_url: https://official.example.org/code/43
source_local_path: source/downloads/code-43.html
source_hash: sha256:...
article_number: "43"
published_on: 2014-01-01
verbatim_status: deterministic_extract
linked_ids:
  - reg-code
---
```

## Legal And High-Stakes Rule

For legal, regulatory, financial, medical, or similarly high-stakes corpora:

- retain the official source locally when allowed
- store exact article/section pointers
- distinguish verbatim text from paraphrase explicitly
- ensure answer-critical artifacts can be traced back to the saved source without requiring the live website
