---
title: "Portuguese Legal QA Seed Benchmark Results - Archive Only"
type: eval_result
status: draft
date: 2026-05-28
---

# Portuguese Legal QA Seed Benchmark Results - Archive Only

Run shape:

- evaluator: main Codex thread
- answerer: fresh sub-agent with no inherited thread context
- allowed context: local benchmark doc plus local `archive-index/`
- web access: not allowed

## Headline

- total questions: `15`
- `pass`: `1`
- `partial`: `2`
- `fail`: `12`
- strict benchmark score: `6.7%` pass rate
- pass-or-partial coverage: `20.0%`

## Read

This is a poor benchmark score, but it is a useful result.

The fresh agent was mostly safe rather than hallucinatory. It answered the three HPP reinvestment questions from local archive support, then correctly refused or downgraded the remaining twelve because the archive does not currently contain those source families or procedures.

So the result is:

- answer quality on covered slices: decent
- archive breadth against this benchmark: weak
- hallucination posture: good

## Per Question

### PT-LAW-001

- grade: `pass`
- reason:
  Hit the net-of-loan reinvestment base, 24/36 month window, prior HPP requirement, and destination-HPP condition.

### PT-LAW-002

- grade: `partial`
- reason:
  Correctly said the intention to reinvest must be declared and that partial reinvestment counts, but missed the benchmark's Annex G and later-declaration details.

### PT-LAW-003

- grade: `partial`
- reason:
  Correctly inferred cumulative land-plus-construction reinvestment from the local extract, but missed the benchmark's documentary-proof point.

### PT-LAW-004

- grade: `fail`
- reason:
  No usable local coverage for tornas in partitioned immovable-property transfers.

### PT-LAW-005

- grade: `fail`
- reason:
  No local inheritance-service coverage for Balcão das Heranças.

### PT-LAW-006

- grade: `fail`
- reason:
  No local inheritance-registration coverage for habilitação plus joint registration.

### PT-LAW-007

- grade: `fail`
- reason:
  No local IMT revalidation procedure coverage.

### PT-LAW-008

- grade: `fail`
- reason:
  No local IMT revalidation channel coverage.

### PT-LAW-009

- grade: `fail`
- reason:
  No local expired-license 2-to-5-year procedure coverage.

### PT-LAW-010

- grade: `fail`
- reason:
  No local expired-license 5-to-10-year procedure coverage.

### PT-LAW-011

- grade: `fail`
- reason:
  No local Segurança Social quarterly-declaration guide coverage.

### PT-LAW-012

- grade: `fail`
- reason:
  No local late quarterly-declaration coverage.

### PT-LAW-013

- grade: `fail`
- reason:
  No local parental-benefit duration coverage.

### PT-LAW-014

- grade: `fail`
- reason:
  No local parental-benefit 30-day extension coverage.

### PT-LAW-015

- grade: `fail`
- reason:
  No local Fundo de Garantia dos Alimentos Devidos a Menores coverage.

## Main Failure Pattern

The result is not mainly a reasoning failure. It is a corpus-coverage failure.

The local archive currently covers:

- HPP reinvestment / CIRS slices
- selected Código da Estrada slices
- selected parliamentary material

The benchmark also asks about:

- inheritance-service procedure
- IMT license revalidation procedure
- Segurança Social contribution procedure
- parental benefits
- family-support fund procedure

Those families are mostly absent from the local archive, so the agent safely abstained.

## Implication

If the goal is to test model behavior on top of the current archive, this run says:

- the archive can answer a narrow covered tax slice reasonably well
- the archive does not yet support this benchmark as a broad Portuguese legal/admin benchmark

If the goal is to build a stronger benchmark loop, the next best move is to split the question set into:

1. `covered-now` questions that should pass on the current archive
2. `stretch` questions that should trigger expansion and later persistence
3. `out-of-coverage` questions that should safely abstain today
