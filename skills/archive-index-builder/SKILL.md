---
name: archive-index-builder
description: Use when designing, scaffolding, or extending a large-document retrieval index for document archives that are too large for full upfront enrichment
---

# Archive Index Builder

Build archive indexes as tiers, not as one monolith.

## Rules

- Treat the index as an evidence router first, not a truth engine.
- Keep global coverage deterministic and cheap.
- Promote only hot or shortlisted documents to expensive extraction tiers.
- Keep provenance first-class: document id, page/block pointer, and confidence.
- Preserve raw canonical source material locally whenever licensing and policy allow.
- Prefer deterministic extraction over LLM-written corpus text.
- Keep verbatim evidence separate from summaries, crosswalks, and other derived notes.
- Never let an LLM-authored artifact be the only surviving representation of a canonical source.
- Separate `speaker said X` from `X is true`.
- If the user provides a URL, inspect it first and infer the likely corpus shape before asking intake questions.
- Prefer agent-driven workflows over custom code in the first version.
- Download only the slice needed for the agreed scope.
- Reuse existing repository scripts before inventing new helpers.
- Prefer `markdown.new` for first-version URL fetch and crawl when the source is public and the output should become Markdown artifacts.
- Treat raw HTML, client-side JavaScript, menus, and page chrome as audit artifacts, not as the model-facing retrieval surface.
- Use browser automation only as a last resort after clean capture and local retrieval paths fail.
- Write agent-facing artifacts as Markdown with frontmatter.
- Maintain a compact navigation index so future queries do not require scanning all files.
- Never lose the source chain from landing page to downloaded file to extracted artifact.
- Track discovered but not yet downloaded items so the index can expand deliberately later.
- Create and maintain a local archive-usage document for future agents, separate from this generic skill.
- Treat user questions as enrichment triggers, not just retrieval requests.
- Do not stop at `not indexed yet` when the missing slice can be built safely inside policy.
- Prefer `query -> measure coverage -> promote local -> expand adjacent -> answer` over `query -> fail -> ask user`.
- Prefer `local archive -> canonical official source -> enrich archive -> answer` over generic web search.
- Distinguish `enrich to answer now` from `persist as durable archive knowledge`.
- Treat rebuildable index files as generated outputs, not handwritten knowledge.
- Give operators a local wrapper for archive checks so they do not have to hand-manage temp JSON files for verifier payloads.
- When scaffolding operator guidance, make Python entrypoints explicit: default to `uv run python` for wrapper checks that read recipe/config YAML or rely on project-installed packages.
- When subagents are available, prefer spawning them for isolated archive subtasks such as source discovery, one-source fetch and indexing, narrow verification, or parallel evidence checks.
- Keep the main thread responsible for the final synthesis, persistence decision, and answer posture.

## Tiers

- `L0`: registry metadata, raw-source pointers, deterministic routing fields
- `L1`: verbatim or deterministically extracted sections, blocks, or article units
- `L2`: claims, references, entities, evidence pointers
- `L3`: canonical links to laws, votes, reports, and external sources

Read [references/index-tiers.md](references/index-tiers.md) before changing tier boundaries or promotion policy.

## Workflow

1. If the user provided a seed URL or landing page, inspect the source first.
2. Infer the likely corpus type, navigation pattern, and candidate retrieval unit from the source.
3. Ask adaptive intake questions based on that inferred corpus shape.
4. Define the corpus registry and retrieval unit.
5. Create or update the archive workspace structure.
6. Acquire only the agreed seed slice of the corpus, preferably through canonical official downloads first and `markdown.new` for public navigation pages.
7. Persist the raw source locally with fetch metadata, hashes, and source-chain fields.
8. Reuse existing scripts and deterministic parsing where they fit, producing verbatim or near-verbatim extract units before any LLM enrichment.
9. When subagents are available, delegate bounded subtasks that can run independently, such as exploring one source family, fetching one official document, indexing one PDF, or validating one evidence branch.
10. Write Markdown artifacts and update the navigation index.
11. Record adjacent discovered items even when they are not downloaded yet.
12. Add promotion rules so repeated hits graduate documents from `L0` to `L1` or `L2`.
13. Only then add LLM-based enrichment for ambiguous normalization or synthesis.
14. For future questions, treat gaps in coverage as work to do, not as the end of the workflow.
15. Write or update a local archive-usage document that tells later agents how to use this specific archive and what policy/config it follows, including the acquisition fallback order for web sources and PDFs.
16. After the archive is usable, point the operator to the companion `archive-evals` skill to validate retrieval, grounding, and boundary behavior.

Read [references/source-inspection.md](references/source-inspection.md) before inspecting a seed URL.
Read [references/intake-questions.md](references/intake-questions.md) before asking questions.
Read [references/acquisition.md](references/acquisition.md) before fetching or crawling sources.
Read [references/metadata-and-index-quality.md](references/metadata-and-index-quality.md) before defining metadata fields or writing the navigation index.
Read [references/retrieval-confidence-and-coverage.md](references/retrieval-confidence-and-coverage.md) before answering topical questions from the archive.
Read [references/archive-management-defaults.md](references/archive-management-defaults.md) before deciding whether to expand, promote, or stop.
Read [references/artifact-contract.md](references/artifact-contract.md) before writing artifacts.
Read [references/navigation-index.md](references/navigation-index.md) before defining query behavior.
Read [references/source-and-expansion.md](references/source-and-expansion.md) before defining discovery, download, or expansion behavior.
Read [references/question-driven-enrichment.md](references/question-driven-enrichment.md) before answering any question whose needed slice is only partially indexed.
After a meaningful build, use the separate `archive-evals` skill to generate and run a small eval suite for the archive.

When a source family is unfamiliar or the cheapest trustworthy fetch path is unclear, use the repo-local `canonical-source-explorer` skill before locking in archive acquisition rules.

## Source Inspection

When the user points the skill at a URL, do not ask generic setup questions immediately.

- Open the page and identify whether it looks like an index page, search page, listing page, canonical document page, or file endpoint.
- Extract the most likely corpus clues first: document families, date ranges, hierarchy labels, file links, filters, and stable identifiers.
- Form a tentative corpus hypothesis such as `parliamentary diaries`, `legal gazette`, `minutes archive`, or `policy reports`.
- Ask questions that resolve ambiguity in that hypothesis rather than starting from zero.

Source inspection is for narrowing the intake, not for silently committing to a crawl plan.

## Intake

Ask a small core set of questions first, then only ask follow-ups when the source leaves ambiguity.

- corpus objective: what questions should this index answer?
- output location: where should the archive workspace live?
- retrieval unit: document, section, debate block, article, or another unit?
- operating mode: should this archive optimize for `accuracy_first`, `balanced`, or `speed_first`?
- evidence contract: what provenance is required in answers?
- autonomy policy: should the archive proactively extract and expand missing slices while answering, or ask first?
- minimum confidence: what minimum answer confidence should the archive aim for before stopping?

Then ask follow-ups only when needed:

- should this link to canonical external sources?
- should ingestion stay registry-only at first, or build block artifacts immediately?
- which metadata fields matter most?
- how should freshness or recrawling work?
- when the index finds adjacent undiscovered or undownloaded material, should it ask before expanding?

The skill must ask questions before indexing. Do not skip intake just because the source looks familiar.
The skill must persist the user's autonomy preference and minimum-confidence preference into the archive policy/config and reuse them on later questions.
The skill should recommend an `operating mode` based on corpus type, but let the user override it:

- `accuracy_first` for laws, regulation, medicine, finance, and similar high-stakes corpora
- `balanced` by default for most document archives
- `speed_first` for exploratory, monitoring, or low-stakes discovery corpora

When the corpus is legal, regulatory, policy, or otherwise high-stakes, the skill should also settle:

- whether raw downloads must be retained
- whether article/section-level verbatim extracts are required
- which source is the ultimate canonical reference
- how consolidated versions and effective dates will be tracked

## Retrieval Unit

Prefer debate blocks, interventions, agenda items, or vote sections over fixed token chunks.
For statutes, codes, regulations, and similar corpora, prefer article/section-level units over free-form chunks.

## Persistence Policy

Do not treat every enrichment step as durable archive material.

When an in-bounds official source is actually used to answer, persist it by default unless there is a clear skip reason.

Persist when the content is:

- canonical
- reusable
- general rather than user-specific
- likely to be asked again

Good candidates to persist:

- regimes
- eligibility rules
- requirements and thresholds
- annual official tables
- official FAQs
- binding or authoritative interpretations
- crosswalks between the legal text and practical use

Do not persist when the work is mainly:

- an ad hoc application to one user case
- a one-off simulation or calculation
- a temporary combination of facts already persisted elsewhere

For official sources, use this capture ladder:

1. official URL discovered: record it as a canonical pointer if not already known
2. official URL used to answer: persist the raw source locally by default
3. reusable rule, table, or section extracted from it: persist an atomic extract artifact

Allowed skip reasons for not persisting an official source:

- duplicate of already saved source
- transient navigation or search page with no durable content
- out of archive scope
- purely user-specific output derived from already-persisted facts

If an official source was consulted but not persisted, record the skip reason explicitly.

Examples:

- persist: `imt-jovem-elegibilidade`
- persist: `imt-tabelas-2025`
- persist: `imt-tabelas-2026`
- persist: `garantia-publica-credito-habitacao`
- persist: `copropriedade-um-cumpre-outro-nao`
- do not persist: `para 455k e 50/50 dá X`

## Granularity

Prefer atomic notes over large mixed notes.

Separate knowledge by:

- topic
- legal regime
- effective period or year

Avoid artifacts that mix:

- rules
- calculations
- FAQs
- concrete user cases

If the answer is only a combination of already-persisted facts, answer from those facts without creating a new artifact.

## Volatility

Handle time-sensitive content explicitly.

- if a rule changes by year, persist it with `effective_date`, `tax_year`, or an equivalent field
- if the answer depends on annual official tables, store only the essential structured values plus the canonical link
- if an artifact contains temporal values, mark clearly when it was verified

Use explicit markers such as:

- `effective_date: YYYY-MM-DD`
- `tax_year: YYYY`
- `verified_at: YYYY-MM-DD`

## Official Source Capture

Bias toward making the archive more local and more official over time.

Default policy:

- official source discovered: register
- official source used in answering: capture locally
- exact wording relied upon: require saved source or saved extract artifact before treating the wording as settled

For annual tables or time-bound official materials:

- save the canonical source or a stable local representation
- persist only the essential structured values needed for reuse
- keep the canonical link and verification date

## Decision Records

Before `expand`, `persist`, or `skip_persist`, write a compact structured decision record.

Minimum fields:

- `action`: `answer`, `expand`, `persist`, or `skip_persist`
- `reason`
- `source_type`: `official` or `unofficial`
- `scope_status`: `in_bounds`, `out_of_bounds`, or `insufficient_input`
- `artifact_kind`: `canonical`, `reusable`, `ad_hoc`, `extract`, `derived_summary`, `annual_values`, `crosswalk`, `resolution`, `calculation`, or `temporary_case_note`
- `skip_reason` when `action=skip_persist`

Allowed `skip_reason` values:

- `duplicate`
- `transient_page`
- `out_of_scope`
- `user_specific`
- `insufficient_value`
- `policy_blocked`

The LLM may choose the action, but the action should not proceed until the deterministic verifier accepts the decision record.

Use `duplicate` when the reusable artifact already exists.
Use `insufficient_value` when the candidate artifact is not a literal duplicate but still adds no durable reusable value.
Use `scope_status: insufficient_input` when the topic is too underspecified to classify the next step honestly.

## Persistence Decision Rule

Use this simple decision rule when deciding whether to create a new artifact:

- new general rule discovered: persist
- new relevant annual value discovered: persist
- official but rare interpretation with durable value: persist
- one-off calculation for this user: do not persist
- only a new combination of already-persisted facts: answer without creating a new artifact

## Execution Model

- Inspect the source.
- Ask intake questions.
- Acquire the selected slice, preferring canonical downloads for source documents and `markdown.new` for public navigation pages.
- Persist raw source files and acquisition metadata locally.
- Run existing local scripts where helpful.
- Write deterministic extract artifacts before any interpretive notes.
- Write Markdown artifacts.
- Rebuild or update the navigation index with a deterministic script.
- Preserve discovered-but-not-downloaded candidates for future expansion.
- Write a decision record before `expand`, `persist`, or `skip_persist`.
- Run deterministic verifiers before claiming coverage is enough, before expanding, and before finalizing answer-critical synthesis.
- Return coverage and confidence details for topical answers.
- Stop once the agreed queryable slice is ready.

Read [references/verifier-toolkit.md](references/verifier-toolkit.md) before designing archive-side policy checks.

Never hand-edit rebuildable index outputs such as `documents.jsonl`, `links.jsonl`, or `navigation.sqlite`. Update the source artifacts and run the rebuild utility instead.

## Question-Driven Enrichment

After the initial build, the archive should grow through use.

When the user asks a question:

1. Query the current archive first.
2. Measure whether current coverage is enough to answer responsibly.
3. If not enough, promote relevant local material before downloading anything new.
4. If still not enough, expand into adjacent discovered material automatically when policy allows.
5. If the needed slice is outside current local coverage but still clearly inside the agreed corpus, fetch and index that slice from canonical official sources when available.
6. Compare the resulting answer confidence against the saved minimum-confidence target.
7. If the answer is still below the saved threshold and expansion is still in-bounds, continue enriching.
8. Rebuild the navigation layer.
9. Run the deterministic verifiers appropriate to the archive mode.
10. Answer from the newly enriched archive with an explicit retrieval report, preferring verbatim extract units over summaries for the decisive evidence.

`Not indexed yet` is a coverage diagnosis, not a terminal answer, unless:

- the next expansion crosses the agreed policy boundary
- the source is inaccessible or authenticated
- the expected cost/scope jump is large enough that the user should approve it first
- the archive cannot reach the saved minimum-confidence target without crossing a real boundary

The skill should feel like an archive operator that keeps building the missing slice until the question is answerable or a real boundary is reached.
Generic web search is fallback behavior, not the primary enrichment path, when official canonical sources are identifiable.

## Default Archive Management

After the initial intake, treat archive management as hands-off by default.

- Query the current archive first.
- Measure coverage before concluding.
- Promote artifacts locally when the needed material already exists in downloaded or processed sources.
- Expand into adjacent discovered material automatically when expansion stays inside the agreed policy boundary.
- If the relevant slice is missing but clearly identifiable, acquire and index that slice automatically when it remains inside policy.
- Ask the user before expanding only when the next step crosses the agreed boundary for scope, cost, or corpus.

The skill should behave like a research operator, not a passive note-taker.
If the user chose a proactive autonomy policy during intake, the skill should remember that and bias toward self-directed enrichment on future questions without asking again for in-bounds expansions.
`operating_mode` should also be persisted and reused. It should affect:

- how much evidence is required before answering
- how easily the archive may expand automatically
- whether canonical-source and extract-level checks are mandatory
- how strictly negative claims are blocked

## Acquisition

For public web sources, prefer `markdown.new` as the first acquisition path because it yields clean Markdown quickly and reduces crawler-specific code.

- use `markdown.new/<url>` or the service API for single-page capture
- use `markdown.new` crawl mode for bounded seed crawls when appropriate
- if that fails, prefer another clean conversion path such as `r.jina.ai` before considering a browser
- do not feed raw HTML, bundled JavaScript, or site chrome directly into model-facing retrieval when a clean Markdown capture is possible
- only escalate to an agent browser when the page depends on live interaction or JavaScript rendering and the cheaper capture paths failed
- persist all returned content locally
- keep the original source URL and parent discovery URL in local artifacts

For canonical source documents, prefer direct local preservation of the official source artifact when feasible:

- download the official HTML, PDF, XML, or equivalent source
- record fetch timestamp and content hash
- keep a stable local path to the raw source
- derive verbatim extract units from the local source before writing summaries

Fallback to direct downloads or local scripts when:

- the source is not public
- the source needs authenticated access
- the service output is incomplete
- the source file is better handled locally, such as a PDF already available in a stable endpoint

## Workspace

Use a Markdown-first archive with a lightweight navigation layer. A typical layout is:

```bash
archive-index/
  AGENTS.md
  artifacts/
    registry/
    blocks/
    extracts/
    claims/
    references/
    entities/
    resolutions/
  index/
    navigation.sqlite
    documents.jsonl
    links.jsonl
  source/
    downloads/
    extracted/
    manifests/
  config/
    index-policy.yaml
```

The navigation index is a locator layer, not the source of truth.

The local `AGENTS.md` inside the archive workspace is not the generic builder skill. It is the agent-facing operating note for this specific archive instance and should include:

- current corpus/scope
- saved autonomy policy
- saved minimum-confidence target
- retrieval unit
- provenance expectations
- whether to enrich proactively or ask first
- where the navigation index lives

## Optional Scaffold

If a starter workspace does not exist yet, the bundled helper may be used:

```bash
python skills/archive-index-builder/scripts/scaffold_archive_index.py path/to/archive-index
```

Read [references/query-and-promotion.md](references/query-and-promotion.md) when implementing query flows or lazy promotion.
