# DR Legislation Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a real `Diário da República` corpus inside `/Users/alexandre/dev/parliament/archive-index` with a recent-window outer map and a deep tax vertical anchored on `IRC`, while preserving one shared navigation graph with the existing `DAR` archive.

**Architecture:** Add a focused archive-index module set under `src/parliament/` for corpus-aware artifact IO, DR discovery, navigation-index rebuilds, and tax-vertical promotion. Keep Markdown/frontmatter as the agent-facing source of truth, with `navigation.sqlite`, `documents.jsonl`, and `links.jsonl` rebuilt deterministically from artifacts.

**Tech Stack:** Python, uv, pytest, PyYAML, SQLite, Markdown + YAML frontmatter, lightweight HTML fetch/parsing

---

### Task 1: Create Archive Index Core Models And Paths

**Files:**
- Create: `src/parliament/archive_index/__init__.py`
- Create: `src/parliament/archive_index/models.py`
- Create: `src/parliament/archive_index/paths.py`
- Create: `tests/unit/test_archive_index_paths.py`

- [ ] **Step 1: Write the failing tests**

Add tests that assert:
- archive roots derive stable corpus-specific directories for `dar` and `dr`
- DR paths include `registry`, `acts`, `article-blocks`, `consolidation-notes`, `relations`, and `facets`
- artifact IDs and filenames remain deterministic for registry and promoted DR artifacts

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_archive_index_paths.py -q`
Expected: failure because archive-index path/model code does not exist yet

- [ ] **Step 3: Write the minimal implementation**

Implement:
- a small `ArchiveIndexPaths` model rooted at `/Users/alexandre/dev/parliament/archive-index`
- corpus-aware path helpers for `dar` and `dr`
- typed models or dataclasses for archive artifacts and link edges only as far as needed by tests

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_archive_index_paths.py -q`
Expected: pass

- [ ] **Step 5: Commit**

```bash
git add src/parliament/archive_index/__init__.py src/parliament/archive_index/models.py src/parliament/archive_index/paths.py tests/unit/test_archive_index_paths.py
git commit -m "feat: add archive index core models and paths"
```

### Task 2: Implement Generic Archive Artifact Reader/Writer For DR Corpus

**Files:**
- Create: `src/parliament/archive_index/artifacts.py`
- Create: `tests/unit/test_archive_index_artifacts.py`
- Modify: `src/parliament/render/frontmatter.py`

- [ ] **Step 1: Write the failing tests**

Add tests that assert:
- Markdown artifacts with frontmatter can be written and read back for DR `registry`, `act`, `article_block`, `consolidation_note`, `relation`, and `facet`
- optional fields are omitted cleanly from frontmatter
- link fields are preserved exactly

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_archive_index_artifacts.py -q`
Expected: failure because the generic archive artifact reader/writer does not exist yet

- [ ] **Step 3: Write the minimal implementation**

Implement:
- a generic `write_archive_artifact(path, frontmatter, body)` helper using existing frontmatter rendering
- a generic `read_archive_artifact(path)` helper that returns parsed metadata + body
- only minimal changes to `render_frontmatter.py` if tests expose a formatting problem

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_archive_index_artifacts.py -q`
Expected: pass

- [ ] **Step 5: Commit**

```bash
git add src/parliament/archive_index/artifacts.py src/parliament/render/frontmatter.py tests/unit/test_archive_index_artifacts.py
git commit -m "feat: add generic archive artifact io"
```

### Task 3: Implement DR Discovery And Recent Outer-Map Registry Capture

**Files:**
- Create: `src/parliament/dr/__init__.py`
- Create: `src/parliament/dr/client.py`
- Create: `src/parliament/dr/discovery.py`
- Create: `tests/unit/test_dr_discovery.py`
- Create: `tests/fixtures/dr/legislacao-por-data.html`
- Create: `tests/fixtures/dr/act-detail.html`

- [ ] **Step 1: Write the failing tests**

Add tests that assert:
- a saved `legislacao-por-data` fixture yields discovered acts with observed metadata
- canonical act URLs are normalized from browse results
- visible `theme` / `code` memberships are captured when present
- discovery output distinguishes observed metadata from inferred metadata

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_dr_discovery.py -q`
Expected: failure because DR discovery code does not exist yet

- [ ] **Step 3: Write the minimal implementation**

Implement:
- a lightweight DR HTTP client with fixture-friendly fetch hooks
- parsers for recent `por data` listings and act detail pages
- a discovery routine that emits shallow DR registry payloads and facet metadata without promoting anything yet

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_dr_discovery.py -q`
Expected: pass

- [ ] **Step 5: Commit**

```bash
git add src/parliament/dr/__init__.py src/parliament/dr/client.py src/parliament/dr/discovery.py tests/unit/test_dr_discovery.py tests/fixtures/dr/legislacao-por-data.html tests/fixtures/dr/act-detail.html
git commit -m "feat: add dr discovery for recent outer map"
```

### Task 4: Implement Navigation Index Rebuilder And Query Support

**Files:**
- Create: `src/parliament/archive_index/navigation.py`
- Create: `tests/unit/test_archive_index_navigation.py`
- Modify: `src/parliament/cli.py`
- Modify: `tests/unit/test_cli.py`

- [ ] **Step 1: Write the failing tests**

Add tests that assert:
- the navigation rebuilder scans both `dar` and `dr` artifacts
- `documents.jsonl`, `links.jsonl`, and `navigation.sqlite` are rebuilt deterministically
- `sqlite` documents table includes normalized dates, titles, paths, confidence, and search text
- the CLI exposes archive commands such as `archive rebuild-index`

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_archive_index_navigation.py tests/unit/test_cli.py -q`
Expected: failure because the dedicated rebuilder and CLI command do not exist yet

- [ ] **Step 3: Write the minimal implementation**

Implement:
- a reusable navigation-index rebuild function
- SQLite and JSONL output generation from Markdown artifacts
- CLI wiring for rebuilding the archive index

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_archive_index_navigation.py tests/unit/test_cli.py -q`
Expected: pass

- [ ] **Step 5: Commit**

```bash
git add src/parliament/archive_index/navigation.py src/parliament/cli.py tests/unit/test_archive_index_navigation.py tests/unit/test_cli.py
git commit -m "feat: add archive navigation index rebuild"
```

### Task 5: Implement DR Registry Write Flow And Recent Outer-Map Build Command

**Files:**
- Create: `src/parliament/archive_index/dr_build.py`
- Create: `tests/integration/test_dr_outer_map_build.py`
- Modify: `src/parliament/cli.py`

- [ ] **Step 1: Write the failing integration test**

Add an integration test that:
- loads DR fixtures for a recent-window crawl
- writes DR `registry` artifacts under `archive-index/artifacts/dr/registry`
- writes observed `facet` artifacts or facet metadata
- rebuilds the shared navigation index and asserts DR entries appear there

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_dr_outer_map_build.py -q`
Expected: failure because the DR build command and writer flow do not exist yet

- [ ] **Step 3: Write the minimal implementation**

Implement:
- a DR outer-map build routine that consumes discovery output
- archive artifact emission for recent-window DR registry records
- CLI wiring such as `archive build-dr-outer-map`

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_dr_outer_map_build.py -q`
Expected: pass

- [ ] **Step 5: Commit**

```bash
git add src/parliament/archive_index/dr_build.py src/parliament/cli.py tests/integration/test_dr_outer_map_build.py
git commit -m "feat: add dr outer map build flow"
```

### Task 6: Implement Tax Vertical Promotion For IRC And Related Acts

**Files:**
- Create: `src/parliament/dr/tax_vertical.py`
- Create: `tests/unit/test_dr_tax_vertical.py`
- Create: `tests/fixtures/dr/irc-act-detail.html`
- Create: `tests/fixtures/dr/irc-consolidated.html`

- [ ] **Step 1: Write the failing tests**

Add tests that assert:
- the tax vertical starts from an `IRC` anchor
- related acts can be discovered and accepted when they remain inside policy
- relevant provisions are promoted into `article_block` artifacts
- consolidation notes are created when multiple provisions are needed for one answer

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_dr_tax_vertical.py -q`
Expected: failure because tax promotion code does not exist yet

- [ ] **Step 3: Write the minimal implementation**

Implement:
- tax-vertical promotion logic rooted in `IRC`
- extraction of exact legal provisions into `article_block` artifacts
- `consolidation_note` generation from multiple related provisions using deterministic assembly first, not LLM-only synthesis

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_dr_tax_vertical.py -q`
Expected: pass

- [ ] **Step 5: Commit**

```bash
git add src/parliament/dr/tax_vertical.py tests/unit/test_dr_tax_vertical.py tests/fixtures/dr/irc-act-detail.html tests/fixtures/dr/irc-consolidated.html
git commit -m "feat: add dr tax vertical promotion"
```

### Task 7: Implement Cross-Corpus Links Between DAR And DR

**Files:**
- Create: `src/parliament/archive_index/linking.py`
- Create: `tests/unit/test_archive_index_linking.py`
- Modify: `src/parliament/archive_index/dr_build.py`
- Modify: `src/parliament/dr/tax_vertical.py`

- [ ] **Step 1: Write the failing tests**

Add tests that assert:
- a DAR reference can resolve to a DR act
- a DR consolidation note can be linked back from a DAR resolution
- link edges are emitted consistently into the shared navigation graph

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_archive_index_linking.py -q`
Expected: failure because cross-corpus link generation does not exist yet

- [ ] **Step 3: Write the minimal implementation**

Implement:
- reusable helpers for `dar -> dr` and `dr -> dar` link emission
- automatic link generation for known canonical anchors such as `Agenda do Trabalho Digno`
- hooks so the DR build and tax-vertical promotion flows can add cross-corpus links without hardcoding everything inline

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_archive_index_linking.py -q`
Expected: pass

- [ ] **Step 5: Commit**

```bash
git add src/parliament/archive_index/linking.py src/parliament/archive_index/dr_build.py src/parliament/dr/tax_vertical.py tests/unit/test_archive_index_linking.py
git commit -m "feat: add dar dr cross corpus linking"
```

### Task 8: Migrate Archive Layout And Seed Initial DR Corpus

**Files:**
- Modify: `/Users/alexandre/dev/parliament/archive-index/README.md`
- Modify: `/Users/alexandre/dev/parliament/archive-index/artifacts/references/ref-agenda-do-trabalho-digno.md`
- Create: `/Users/alexandre/dev/parliament/archive-index/artifacts/dr/registry/.gitkeep`
- Create: `/Users/alexandre/dev/parliament/archive-index/artifacts/dr/acts/.gitkeep`
- Create: `/Users/alexandre/dev/parliament/archive-index/artifacts/dr/article-blocks/.gitkeep`
- Create: `/Users/alexandre/dev/parliament/archive-index/artifacts/dr/consolidation-notes/.gitkeep`
- Create: `/Users/alexandre/dev/parliament/archive-index/artifacts/dr/relations/.gitkeep`
- Create: `/Users/alexandre/dev/parliament/archive-index/artifacts/dr/facets/.gitkeep`
- Create: `/Users/alexandre/dev/parliament/tests/integration/test_archive_seed_build.py`

- [ ] **Step 1: Write the failing integration test**

Add an integration test that:
- builds the DR outer map into the new `artifacts/dr/*` structure
- preserves the existing DAR archive
- keeps the existing labour-law bridge working after the directory migration
- rebuilds the shared index successfully

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_archive_seed_build.py -q`
Expected: failure because the archive layout migration and seed workflow do not exist yet

- [ ] **Step 3: Write the minimal implementation**

Implement:
- the DR artifact directory migration
- seed commands or scripts for the first recent-window DR build
- README updates that explain how to refresh the outer map and tax vertical

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_archive_seed_build.py -q`
Expected: pass

- [ ] **Step 5: Commit**

```bash
git add /Users/alexandre/dev/parliament/archive-index/README.md /Users/alexandre/dev/parliament/archive-index/artifacts/dr /Users/alexandre/dev/parliament/tests/integration/test_archive_seed_build.py
git commit -m "feat: seed dr archive corpus"
```

### Task 9: Full Verification

**Files:**
- Modify: none
- Test: `tests/unit/test_archive_index_paths.py`
- Test: `tests/unit/test_archive_index_artifacts.py`
- Test: `tests/unit/test_dr_discovery.py`
- Test: `tests/unit/test_archive_index_navigation.py`
- Test: `tests/unit/test_dr_tax_vertical.py`
- Test: `tests/unit/test_archive_index_linking.py`
- Test: `tests/integration/test_dr_outer_map_build.py`
- Test: `tests/integration/test_archive_seed_build.py`

- [ ] **Step 1: Run the targeted unit and integration suite**

Run:

```bash
uv run pytest \
  tests/unit/test_archive_index_paths.py \
  tests/unit/test_archive_index_artifacts.py \
  tests/unit/test_dr_discovery.py \
  tests/unit/test_archive_index_navigation.py \
  tests/unit/test_dr_tax_vertical.py \
  tests/unit/test_archive_index_linking.py \
  tests/integration/test_dr_outer_map_build.py \
  tests/integration/test_archive_seed_build.py -q
```

Expected: pass

- [ ] **Step 2: Run the archive rebuild command against the real workspace**

Run:

```bash
uv run python -m parliament.cli archive rebuild-index --root /Users/alexandre/dev/parliament/archive-index
```

Expected: `documents.jsonl`, `links.jsonl`, and `navigation.sqlite` rebuilt without manual inline scripts

- [ ] **Step 3: Run the first real DR outer-map build**

Run:

```bash
uv run python -m parliament.cli archive build-dr-outer-map \
  --root /Users/alexandre/dev/parliament/archive-index \
  --window recent
```

Expected: recent-window DR `registry` artifacts and facet coverage written under `artifacts/dr/`

- [ ] **Step 4: Run the first tax vertical build**

Run:

```bash
uv run python -m parliament.cli archive build-dr-tax-vertical \
  --root /Users/alexandre/dev/parliament/archive-index \
  --anchor irc
```

Expected: promoted `act`, `article_block`, `consolidation_note`, and `relation` artifacts for the first tax slice

- [ ] **Step 5: Commit**

```bash
git add src tests archive-index docs/superpowers/plans/2026-05-23-dr-legislation-index.md
git commit -m "feat: add dr legislation archive index"
```
