---
title: "feat: Add archive-local consultation runtime slice"
type: feat
status: completed
date: 2026-06-05
---

# feat: Add archive-local consultation runtime slice

## Summary

Ship the first bounded slice of the broader agent-native operator plan:

- define one explicit consultation runtime contract
- add a package-owned deterministic consultation module
- generate an archive-local `scripts/consult_archive.py` wrapper
- emit a machine-readable consultation audit artifact that the human and agent can both inspect

This slice does not attempt to solve the entire operator surface. It standardizes the first gate: given a question and optional user facts, tell the operator whether the next step is `decisive_answer`, `expand`, or `ask_user`, and show the evidence/state behind that outcome.

---

## Scope Boundaries

### In scope

- consultation contract doc
- package consultation runtime
- archive-local consultation wrapper generation
- machine-readable audit artifact
- minimal archive state summary artifact if needed by the runtime
- scaffold and runtime tests

### Out of scope

- full package extraction of `run_archive_check.py`
- broad lifecycle/CRUD helper work
- structured domain-pack validation migration
- full answer synthesis or model-driven response generation
- every discovery/doc cleanup from the larger plan

---

## Requirements

- R1. A generated archive exposes a first-class consultation wrapper at `scripts/consult_archive.py`.
- R2. The consultation wrapper delegates to package-owned runtime code rather than embedding logic locally.
- R3. The runtime classifies a question as `rule_lookup`, `case_application`, or `archive_audit`.
- R4. The runtime emits one machine-readable audit artifact containing classification, support state, currentness state, missing-user-facts state, candidate artifacts, and final outcome.
- R5. The runtime supports three outcomes only in this slice: `decisive_answer`, `expand`, and `ask_user`.
- R6. The runtime reuses existing archive policy rails where practical instead of inventing duplicate check logic.
- R7. Generated archive docs point operators at the consultation wrapper as the primary entrypoint from inside the archive repo.

---

## Implementation Units

### U1. Define the consultation contract

- **Goal:** Create one explicit reference contract for the consultation runtime.
- **Files:** `skills/archive-operator/references/consultation-runtime-contract.md`
- **Approach:** Document question-shape classification, outcome semantics, audit payload fields, and the precedence model for this reduced slice.
- **Verification:** The runtime can be implemented from the contract without relying on implied behavior in scattered docs.

### U2. Add a package consultation runtime

- **Goal:** Implement a deterministic consultation module under `src/ledger/`.
- **Files:** `src/ledger/consultation/`, relevant tests
- **Approach:** The runtime should:
  - classify the question
  - detect whether user facts are missing for case-application style questions
  - inspect archive documents and minimal state artifacts
  - infer whether the question is currentness-sensitive
  - return `decisive_answer`, `expand`, or `ask_user` with a machine-readable audit payload
- **Verification:** Package tests cover all three outcome types and audit field emission.

### U3. Generate an archive-local wrapper and wire docs

- **Goal:** Make consultation usable from inside a scaffolded archive repo.
- **Files:** `skills/archive-index-builder/scripts/scaffold_archive_index.py`, scaffold tests
- **Approach:** Generate `scripts/consult_archive.py`, mention it in generated docs, and ensure it writes its audit artifact into the archive workspace.
- **Verification:** A scaffolded archive contains the wrapper and a local consultation run succeeds.
