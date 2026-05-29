---
title: "Portuguese Legal QA Seed Benchmark Results - Growing Operator"
type: eval_result
status: draft
date: 2026-05-28
---

# Portuguese Legal QA Seed Benchmark Results - Growing Operator

Run shape:

- evaluator: main Codex thread
- answerer: archive-growing operator flow in the local repo
- archive posture: local archive first, then canonical official-source expansion when coverage was missing
- persistence: enabled
- web access: allowed, but only to canonical official sources for in-bounds missing slices

## What Changed During The Run

The operator expanded and persisted the following new archive slices before re-grading:

- `ext-at-faq-5869-tornas-irs`
- `ext-justica-balcao-herancas-servicos`
- `ext-justica-heranca-registo-em-comum`
- `ext-imt-revalidacao-prazo-e-canais`
- `ext-imt-revalidacao-caducada-2a5-anos`
- `ext-imt-revalidacao-caducada-5a10-anos`
- `note-heranca-balcao-servicos`
- `note-imt-revalidacao-carta`

Rebuild proof after persistence:

- `python3 archive-index/scripts/rebuild_index.py` -> `173` docs / `130` links
- `python3 archive-index/scripts/check_index_consistency.py` -> `ok: true`
- `uv run python skills/archive-evals/scripts/run_archive_evals.py run archive-index` -> thresholds still green

## Headline

- total questions: `15`
- `pass`: `8`
- `partial`: `2`
- `fail`: `5`
- strict benchmark score: `53.3%` pass rate
- pass-or-partial coverage: `66.7%`

Compared with the archive-only run:

- pass rate improved from `6.7%` to `53.3%`
- pass-or-partial improved from `20.0%` to `66.7%`
- `7` of the previous `12` failures were converted into passes by archive growth

## Per Question

### PT-LAW-001

- grade: `pass`
- reason:
  Existing local CIRS/HPP support was already sufficient.

### PT-LAW-002

- grade: `partial`
- reason:
  Existing local support still gets the core rule right, but this archive slice is not yet as explicit as the benchmark on Annex G and later-declaration detail.

### PT-LAW-003

- grade: `partial`
- reason:
  Existing local support still gets the cumulative reinvestment rule broadly right, but is thinner than the benchmark on documentary-proof detail.

### PT-LAW-004

- grade: `pass`
- reason:
  New Portal das Financas FAQ extract directly states IRS category G treatment, the onerous-transfer basis, the "ainda que delas se prescinda" point, and Annex G reporting.

### PT-LAW-005

- grade: `pass`
- reason:
  New Justica extracts now directly support habilitacao de herdeiros, partilha, and registo dos bens no Balcao das Herancas.

### PT-LAW-006

- grade: `pass`
- reason:
  New Justica extract now directly states that habilitacao can be done with registo dos bens da heranca em comum a favor de todos os herdeiros.

### PT-LAW-007

- grade: `pass`
- reason:
  New IMT extract directly states the six-month pre-expiry window and that the rule follows the applicable age/category table.

### PT-LAW-008

- grade: `pass`
- reason:
  New IMT extract directly lists the channels: IMT Online, IMT desks, Espaco do Cidadao, and Parceiro do IMT.

### PT-LAW-009

- grade: `pass`
- reason:
  New IMT extract directly states the general 2-to-5-year rule: practical test in special exam, no driving-school enrollment, with the under-50 category exception.

### PT-LAW-010

- grade: `pass`
- reason:
  New IMT extract directly states the 5-to-10-year rule: successful completion of a specific training course plus practical test.

### PT-LAW-011

- grade: `fail`
- reason:
  No persisted local Seguranca Social quarterly-declaration source yet. The official source path is still operationally awkward and was not cleanly materialized in this run.

### PT-LAW-012

- grade: `fail`
- reason:
  No persisted local Seguranca Social late quarterly-declaration source yet.

### PT-LAW-013

- grade: `fail`
- reason:
  No persisted local parental-benefit duration slice yet.

### PT-LAW-014

- grade: `fail`
- reason:
  No persisted local parental-benefit 30-day-extension slice yet.

### PT-LAW-015

- grade: `fail`
- reason:
  No persisted local Fundo de Garantia dos Alimentos Devidos a Menores slice yet.

## Read

This is the more faithful test of the product promise.

The archive was not just queried. It was used as an operator surface:

1. query local archive
2. detect missing in-bounds slices
3. fetch canonical official sources
4. persist reusable extracts and notes
5. rebuild the index
6. answer again from the enriched archive

The result is materially better, but still bounded.

What is now proven:

- the archive-growing operator can close straightforward FAQ and service-procedure gaps from official sources
- the second run becomes local for those slices
- the persisted archive breadth is measurably better than the archive-only baseline

What is not yet proven:

- broad multi-family autonomous growth across difficult source families like Seguranca Social app-shell pages and practical-guide documents
- full benchmark closure on the whole 15-question seed set

## Main Remaining Frontier

The next highest-leverage move is not another benchmark doc. It is hardening the growth operator for the remaining source families:

- Seguranca Social practical guides and service pages
- parental-benefit guidance
- family-support-fund procedure

That should be measured with the same shape:

1. cold archive-only run
2. growing-operator run
3. second-run local coverage check
