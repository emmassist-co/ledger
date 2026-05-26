# Parliamentary Transcript Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first end-to-end artifact-first parliamentary transcript workflow, from PDF parsing through section notes, claims/references, and level 1/2/3 views.

**Architecture:** A small Python package will own deterministic extraction, sectioning, artifact IO, and CLI orchestration. OpenRouter-backed LLM tasks will be isolated behind a task-oriented adapter so note writing and rendering can be tested with stubs while remaining runnable against real models.

**Tech Stack:** Python, uv, PyMuPDF / pymupdf4llm, PyYAML, pytest, Markdown + YAML frontmatter

---

### Task 1: Scaffold Package And Tooling

**Files:**
- Create: `pyproject.toml`
- Create: `src/parliament/__init__.py`
- Create: `src/parliament/cli.py`
- Create: `src/parliament/config.py`
- Create: `tests/unit/test_cli.py`

- [ ] **Step 1: Write the failing tests**

Add tests that assert:
- the CLI exposes a `process` command
- config loading can read defaults and explicit config files

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_cli.py -q`
Expected: failure because package and CLI do not exist yet

- [ ] **Step 3: Write the minimal implementation**

Create the package, CLI parser, and config loader with the minimum needed to satisfy the tests.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_cli.py -q`
Expected: pass

### Task 2: Implement Markdown-First PDF Extraction

**Files:**
- Create: `src/parliament/models/document.py`
- Create: `src/parliament/extract/pdf_text.py`
- Create: `src/parliament/extract/page_map.py`
- Create: `tests/unit/test_pdf_text.py`

- [ ] **Step 1: Write the failing tests**

Add tests that assert:
- a synthetic transcript PDF can be extracted into Markdown with page markers
- speaker/procedural lines survive extraction
- page mapping records page numbers and block text

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_pdf_text.py -q`
Expected: failure because extraction code does not exist yet

- [ ] **Step 3: Write the minimal implementation**

Implement Markdown-first extraction using `pymupdf4llm` when available and a PyMuPDF text fallback otherwise.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_pdf_text.py -q`
Expected: pass

### Task 3: Implement Heuristic Section Detection

**Files:**
- Create: `src/parliament/models/section.py`
- Create: `src/parliament/sectioning/heuristics.py`
- Create: `src/parliament/sectioning/normalizer.py`
- Create: `tests/unit/test_sectioning.py`

- [ ] **Step 1: Write the failing tests**

Add tests that assert:
- a transcript-like extracted Markdown sample is split into semantic sections
- IDs are stable and slugged
- long sections can be split into part sections when a size threshold is exceeded

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_sectioning.py -q`
Expected: failure because sectioning code does not exist yet

- [ ] **Step 3: Write the minimal implementation**

Implement heading/speaker/procedural heuristics, stable slugging, and fallback section splitting.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_sectioning.py -q`
Expected: pass

### Task 4: Implement Artifact Models And Writers

**Files:**
- Create: `src/parliament/models/reference.py`
- Create: `src/parliament/models/artifacts.py`
- Create: `src/parliament/io/paths.py`
- Create: `src/parliament/io/writers.py`
- Create: `src/parliament/render/frontmatter.py`
- Create: `tests/unit/test_writers.py`

- [ ] **Step 1: Write the failing tests**

Add tests that assert:
- document output paths are derived correctly
- section notes render valid frontmatter and body sections
- metadata and reference artifacts are written to the expected locations

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_writers.py -q`
Expected: failure because artifact writers do not exist yet

- [ ] **Step 3: Write the minimal implementation**

Implement artifact path derivation and Markdown/JSON writers.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_writers.py -q`
Expected: pass

### Task 5: Implement OpenRouter LLM Adapter And Prompt Loading

**Files:**
- Create: `src/parliament/llm/base.py`
- Create: `src/parliament/llm/openrouter.py`
- Create: `src/parliament/llm/prompts.py`
- Create: `prompts/section-note.md`
- Create: `prompts/claims.md`
- Create: `prompts/level-1.md`
- Create: `prompts/level-2.md`
- Create: `prompts/level-3.md`
- Create: `tests/unit/test_openrouter.py`

- [ ] **Step 1: Write the failing tests**

Add tests that assert:
- prompt templates load from disk
- the OpenRouter client builds the expected request payload
- task methods return parsed string content from a mocked HTTP response

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_openrouter.py -q`
Expected: failure because LLM adapter code does not exist yet

- [ ] **Step 3: Write the minimal implementation**

Implement the task-oriented adapter and prompt loading.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_openrouter.py -q`
Expected: pass

### Task 6: Implement Pipeline Stages For Notes, Claims, Views, And Index

**Files:**
- Create: `src/parliament/pipeline/orchestrator.py`
- Create: `src/parliament/pipeline/stages/parse_pdf.py`
- Create: `src/parliament/pipeline/stages/detect_sections.py`
- Create: `src/parliament/pipeline/stages/write_section_notes.py`
- Create: `src/parliament/pipeline/stages/extract_claims_and_references.py`
- Create: `src/parliament/pipeline/stages/write_index.py`
- Create: `src/parliament/pipeline/stages/render_views.py`
- Create: `tests/unit/test_pipeline_stages.py`

- [ ] **Step 1: Write the failing tests**

Add tests that assert:
- stages transform inputs to outputs with a fake LLM
- claims and references are aggregated from section notes
- the index and views are produced from note artifacts rather than raw section text

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_pipeline_stages.py -q`
Expected: failure because pipeline stage code does not exist yet

- [ ] **Step 3: Write the minimal implementation**

Implement the orchestration and stage logic with dependency injection for the LLM adapter.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_pipeline_stages.py -q`
Expected: pass

### Task 7: Implement End-To-End CLI Processing

**Files:**
- Modify: `src/parliament/cli.py`
- Create: `tests/integration/test_process_command.py`

- [ ] **Step 1: Write the failing test**

Add an integration test that:
- builds a synthetic transcript PDF fixture
- runs the CLI `process` command with a fake LLM
- asserts the expected folder layout and key artifact contents

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_process_command.py -q`
Expected: failure because the command does not yet orchestrate the full pipeline

- [ ] **Step 3: Write the minimal implementation**

Wire the CLI command to the pipeline and artifact writers.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_process_command.py -q`
Expected: pass

### Task 8: Add Repo-Local Skills And Sample Config

**Files:**
- Create: `skills/process-parliamentary-transcript/SKILL.md`
- Create: `skills/pdf-parser/SKILL.md`
- Create: `skills/section-detector/SKILL.md`
- Create: `skills/section-note-writer/SKILL.md`
- Create: `skills/claims-and-references-extractor/SKILL.md`
- Create: `skills/complexity-slider-renderer/SKILL.md`
- Create: `config/models.example.yaml`
- Create: `config/pipeline.example.yaml`
- Create: `README.md`

- [ ] **Step 1: Write the failing tests**

Add tests or assertions that:
- required skill files exist
- sample configs load
- README usage examples reference the actual CLI shape

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_cli.py tests/unit/test_openrouter.py -q`
Expected: failure due to missing skills/config assets or mismatched expectations

- [ ] **Step 3: Write the minimal implementation**

Add the repo-local skills, config examples, and README.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_cli.py tests/unit/test_openrouter.py -q`
Expected: pass

### Task 9: Full Verification

**Files:**
- Verify existing files only

- [ ] **Step 1: Run the full test suite**

Run: `uv run pytest -q`
Expected: all tests pass

- [ ] **Step 2: Run a manual smoke test**

Run the CLI against the synthetic fixture path and inspect the generated document workspace.

- [ ] **Step 3: Confirm known limitations**

Document that external reference resolution and view verification are designed but not implemented in the first end-to-end pass.
