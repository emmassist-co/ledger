---
title: "DR-Only Portuguese Legal Benchmark"
type: eval
status: draft
date: 2026-05-28
---

# DR-Only Portuguese Legal Benchmark

Benchmark seed for evaluating Portuguese legal-rule answers that should be grounded in the `Diario da Republica` itself, not in service pages, FAQs, or procedural portals.

This set is intentionally **not optimized for current archive coverage**.

The point is the opposite:

- force `DR`-specific legal lookup
- allow multi-article synthesis when the rule is genuinely scattered
- reduce "Google-like" answers based on authority help pages
- test whether the model can stay inside statutory/regulatory text

## Default Run Mode

The default benchmark mode is **not** `archive-only`.

The canonical run shape is:

1. ask the question cold
2. require `archive first`
3. if local support is weak, force `expand`
4. constrain expansion to `DR` canonical sources only
5. persist the winning slice
6. answer
7. rerun later and measure whether the same question becomes local

`archive-only` runs are diagnostic only. They may still be useful for measuring current local coverage, but they should not be treated as the main product benchmark.

## Scope Rules

- Preferred source family: `DR` legislation or official `DR` detail pages only
- No authority FAQ or service-page shortcuts
- No "how/where do I submit" procedure questions
- `exact_wording` questions should only pass if backed by `raw_source` or `extract`
- Cross-article synthesis is allowed and expected when the legal rule is distributed across the act

## Suggested Scoring Heuristic

- `pass`: hits all must-hit points with no material legal error and stays within the cited `DR` sources
- `partial`: broadly right but misses an article-level condition, carve-out, timing rule, or scope limitation
- `fail`: contradicts the `DR`, answers a service-procedure question instead of the legal rule, or invents conditions not traceable to the cited act

## Recommended Metrics

- `expand_success_rate`
- `answer_pass_rate_after_expand`
- `wrong_source_rate`
- `persistence_success_rate`
- `second_run_local_hit_rate`

For this benchmark, `wrong_source_rate` should count any answer that settles the question from non-`DR` source families when `DR` expansion was required.

## Questions

### PT-DR-001

- Domain: `tax`
- Question: `Quais sao, em termos legais, as condicoes base para exclusao de tributacao das mais-valias na venda de habitacao propria e permanente com reinvestimento?`
- Expected answer:
  The exclusion depends on reinvesting the realization value net of any acquisition-loan amortization in another qualifying housing destination, within the legal time window from 24 months before to 36 months after the sale. The sold property must have been the taxpayer's own permanent home, normally proved by tax domicile in the prior 12 months, and the new property must be allocated to the same purpose within the legal deadlines.
- Must-hit points:
  - reinvestment base is sale value net of acquisition-loan amortization
  - time window includes `24 months before` and `36 months after`
  - sold property must have been own permanent home
  - replacement property must be allocated to own permanent home within the legal deadlines
- DR source:
  - [Codigo do IRS - artigo 10](https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2014-70048167-70051792)

### PT-DR-002

- Domain: `tax`
- Question: `Se o reinvestimento para exclusao de mais-valias for apenas parcial, qual e a consequencia legal?`
- Expected answer:
  The exclusion only applies proportionally to the part of the gain corresponding to the amount reinvested.
- Must-hit points:
  - partial reinvestment is allowed
  - the exclusion is only proportional, not total
- DR source:
  - [Codigo do IRS - artigo 10](https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2014-70048167-70051792)

### PT-DR-003

- Domain: `tax`
- Question: `Para residentes, como e tratado em IRS o saldo de mais-valias imobiliarias e qual e a excecao principal a regra dos 50%?`
- Expected answer:
  In the ordinary resident case, the positive or negative balance of the relevant real-estate gains is considered only in `50%` of its amount. The main statutory exception is the public-support case described in article 43(2)(a), where the balance is fully considered.
- Must-hit points:
  - ordinary rule is `50%`
  - the rule concerns the net balance of the relevant gains/losses
  - there is a `100%` exception in the specific public-support situation
- DR source:
  - [Codigo do IRS - artigo 43](https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2014-70048167-870334685)

### PT-DR-004

- Domain: `road_traffic`
- Question: `No sistema de pontos do Codigo da Estrada, quantos pontos sao subtraidos por contraordenacao grave e muito grave, e quais sao os principais patamares de consequencias quando os pontos descem?`
- Expected answer:
  A serious offence subtracts `2` points in the ordinary case and `3` in certain aggravated cases. A very serious offence subtracts `4` points in the ordinary case and `5` in certain aggravated cases. The statute then provides progressively heavier consequences at low point totals, including mandatory training, theoretical examination, and eventual cassation when all points are lost.
- Must-hit points:
  - grave: `2` points in the ordinary case
  - muito grave: `4` points in the ordinary case
  - aggravated variants exist
  - low-point consequences include training, exam, and eventual cassation
- DR source:
  - [Codigo da Estrada - artigo 148](https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2013-116041830-116043445)

### PT-DR-005

- Domain: `road_traffic`
- Question: `Quanto dura, em regra, o regime probatorio do titulo de conducao e que tipo de infracoes podem levar a caducidade ou perda do titulo nesse periodo?`
- Expected answer:
  The probationary regime is tied, in ordinary terms, to the first `3 years` of the licence's validity. During that period, one very serious offence or a second serious offence, once backed by final administrative or court decision under the Code's structure, can trigger loss of the title under the probationary regime rules.
- Must-hit points:
  - ordinary duration is `3 years`
  - one `muito grave` can trigger the consequence
  - a `segunda grave` can also trigger it
  - answer should stay inside the probationary-regime rule, not drift into ordinary post-probation penalties
- DR source:
  - [Codigo da Estrada - regime probatorio / titulo](https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2013-116041830)

### PT-DR-006

- Domain: `corporate_tax`
- Question: `Segundo o Codigo do IRC, qual e o criterio geral para um gasto ser fiscalmente dedutivel?`
- Expected answer:
  The general rule is that the expense must be demonstrably indispensable to obtaining taxable income or maintaining the productive source. The answer should remain at the level of the article's deductibility test, not collapse into checklist folklore.
- Must-hit points:
  - indispensability to obtaining taxable income or maintaining the productive source
  - answer should frame this as the general statutory criterion
- DR source:
  - [Codigo do IRC - artigo 23](https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2014-64205634)

### PT-DR-007

- Domain: `corporate_tax`
- Question: `As despesas de representacao, incluindo refeicoes oferecidas a clientes ou fornecedores, estao sujeitas a tributacao autonoma? Em que termos base?`
- Expected answer:
  Yes. Representation expenses are subject to autonomous taxation at `10%`, and the statutory concept includes receptions, meals, travel, and outings offered to clients, suppliers, or other persons/entities. The rate can be increased by `10 percentage points` in loss years, subject to the statutory carve-outs.
- Must-hit points:
  - yes
  - base rate `10%`
  - meals / travel / receptions offered to clients or suppliers are included
  - there is a `+10 p.p.` increase in loss years, subject to carve-outs
- DR source:
  - [Codigo do IRC - artigo 88](https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2014-64205634)

### PT-DR-008

- Domain: `housing_credit`
- Question: `Na garantia publica para credito a habitacao de jovens, basta um dos compradores cumprir os requisitos se a aquisicao for conjunta?`
- Expected answer:
  No. Under the specific regulatory rule, all acquirers of the property must be borrowers under the credit and must satisfy the eligibility conditions.
- Must-hit points:
  - no
  - all acquirers must be borrowers
  - all must satisfy the regime conditions
- DR source:
  - [Portaria n.º 236-A/2024/1 - artigo 3, n.º 13](https://diariodarepublica.pt/dr/detalhe/portaria/236-a-2024-889277003)

### PT-DR-009

- Domain: `housing_credit`
- Question: `Quais sao os elementos nucleares do regime legal da garantia publica para credito a habitacao de jovens, sem entrar em FAQ operacionais?`
- Expected answer:
  At minimum, the answer should identify that the regime is for first own permanent home, applies to young borrowers within the statutory age band, includes fiscal-residence and ownership-history requirements, uses an income ceiling tied to IRS bracket, sets a maximum transaction value, and caps the state guarantee percentage and duration according to the legal regime.
- Must-hit points:
  - first own permanent home
  - age-bounded youth regime
  - fiscal residence / ownership-history conditions
  - income ceiling tied to IRS bracket
  - transaction-value ceiling
  - statutory cap on guarantee percentage and duration
- DR source:
  - [Decreto-Lei n.º 44/2024 - regime base](https://diariodarepublica.pt/dr/legislacao-consolidada/decreto-lei/2024-911531704)
  - [Portaria n.º 236-A/2024/1](https://diariodarepublica.pt/dr/detalhe/portaria/236-a-2024-889277003)

### PT-DR-010

- Domain: `labour`
- Question: `Qual e, em regra, o periodo experimental no contrato de trabalho por tempo indeterminado para a generalidade dos trabalhadores?`
- Expected answer:
  The ordinary rule for the generality of workers is `90 days`.
- Must-hit points:
  - `90 days`
  - answer should identify this as the ordinary/general rule
- DR source:
  - [Codigo do Trabalho - artigo 112](https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2009-34546475-124448627)

### PT-DR-011

- Domain: `labour`
- Question: `Quantos dias de falta justificada sao previstos, em regra, por falecimento de descendente ou afim no 1.º grau da linha reta?`
- Expected answer:
  The current rule is `20 consecutive days`.
- Must-hit points:
  - `20 days`
  - should frame them as justified absences for this specific death category
- DR source:
  - [Codigo do Trabalho - artigo 251](https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2004-34546475)

### PT-DR-012

- Domain: `succession`
- Question: `Quem sao os herdeiros legitimarios segundo o Codigo Civil?`
- Expected answer:
  The forced heirs are the spouse, descendants, and ascendants, by the order and under the rules of legitimate succession.
- Must-hit points:
  - spouse
  - descendants
  - ascendants
  - answer should identify these as `herdeiros legitimarios`
- DR source:
  - [Codigo Civil - artigo 2157](https://diariodarepublica.pt/dr/detalhe/decreto-lei/496-1977-300030)

### PT-DR-013

- Domain: `leases`
- Question: `Num arrendamento urbano com prazo certo, quando pode o arrendatario denunciar o contrato e com que antecedencia minima?`
- Expected answer:
  After one third of the initial term or renewal has elapsed, the tenant may denounce the contract at any time with minimum prior notice of `120 days` if the term is at least one year, or `60 days` if it is under one year.
- Must-hit points:
  - one third of the term must have elapsed
  - `120 days` if term is `>= 1 year`
  - `60 days` if term is `< 1 year`
- DR source:
  - [Codigo Civil - artigo 1098](https://diariodarepublica.pt/redirect/LinkConsolidacaoAntiga.aspx?consolidacaoId=123928118)

## Notes

- This is a `DR`-specific benchmark, not a general Portuguese legal benchmark.
- Several questions are intentionally harder than the current archive's comfort zone.
- The primary benchmark should be run in `DR-only expand mode`, not `archive-only` mode.
- A good reporting split is:
  - `cold_expand_run`
  - `second_run_local_reuse`
  - optional `archive_only_diagnostic`
- A good next split would be:
  - `already-covered-by-archive`
  - `DR-reachable-but-not-yet-materialized`
  - `complex-cross-article synthesis`
- If we operationalize this benchmark, the evaluator should record:
  - whether the answer stayed inside `DR`
  - whether the answer used article-level support
  - whether the answer required multi-article synthesis
  - whether the answer drifted into service/procedure language that the statute itself does not settle
