# Archive Evals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a separate `archive-evals` companion skill that can scaffold, generate, and run small deterministic evals against an archive built with `archive-index-builder`.

**Architecture:** Keep the eval system lightweight. The skill defines the workflow and eval buckets. A small runner script handles deterministic scenario generation and execution from archive metadata and verifier outputs. The builder references the eval skill but does not embed it.

**Tech Stack:** Markdown skills, Python 3, JSON, JSONL, archive-side verifier CLI

---

### Task 1: Add The Archive Evals Skill And References

**Files:**
- Create: `skills/archive-evals/SKILL.md`
- Create: `skills/archive-evals/references/scenario-schema.md`
- Create: `skills/archive-evals/references/buckets-and-reporting.md`

- [ ] **Step 1: Write the skill and reference docs**
- [ ] **Step 2: Verify the workflow matches the approved design**
- [ ] **Step 3: Commit**

### Task 2: Add Minimal Archive Evals Scripts

**Files:**
- Create: `skills/archive-evals/scripts/scaffold_archive_evals.py`
- Create: `skills/archive-evals/scripts/run_archive_evals.py`

- [ ] **Step 1: Scaffold eval workspace support**
- [ ] **Step 2: Add corpus-derived scenario generation**
- [ ] **Step 3: Add deterministic run/report flow**
- [ ] **Step 4: Compile and smoke-test the scripts**
- [ ] **Step 5: Commit**

### Task 3: Link The Builder To The Companion Skill

**Files:**
- Modify: `skills/archive-index-builder/SKILL.md`
- Modify: `skills/archive-index-builder/scripts/scaffold_archive_index.py`

- [ ] **Step 1: Reference the eval companion skill from the builder docs**
- [ ] **Step 2: Mention eval scaffold/runtime in the builder workspace scaffold**
- [ ] **Step 3: Re-run compile and scaffold checks**
- [ ] **Step 4: Commit**
