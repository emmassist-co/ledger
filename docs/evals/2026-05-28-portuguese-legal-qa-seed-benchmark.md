---
title: "Portuguese Legal QA Seed Benchmark"
type: eval
status: draft
date: 2026-05-28
---

# Portuguese Legal QA Seed Benchmark

Seed question set for evaluating a model on common Portuguese legal and administrative-law adjacent questions using official public sources.

This is intentionally separate from the local archive. It is a web-grounded benchmark seed that can be used to:

- ask the model each question cold
- compare the model answer against a compact canonical answer
- score whether it stayed within the official source
- decide which slices are worth importing into the archive later

## Default Run Mode

This benchmark should also default to **expand mode**, not `archive-only`.

Recommended run shape:

1. ask the question cold
2. use the local archive first
3. if support is weak, expand to the canonical official source family for that question
4. persist reusable slices back into the archive
5. answer
6. rerun later to measure whether the slice became local

`archive-only` runs are diagnostic only. Use them to measure current coverage breadth, not as the primary product benchmark.

## How To Use

For each question:

1. Ask only the `Question`.
2. Score the answer against `Expected answer` and `Must-hit points`.
3. Mark `pass`, `partial`, or `fail`.
4. Track whether the model:
   - answered the actual question
   - stayed legally accurate
   - invented conditions not in the source
   - overclaimed case-specific conclusions

## Scoring Heuristic

- `pass`: hits all must-hit points with no material legal error
- `partial`: broadly right, but misses a condition, time limit, or procedural detail
- `fail`: contradicts the source, omits the core rule, or hallucinates the procedure

## Questions

### PT-LAW-001

- Domain: `tax`
- Question: `Quais são as condições para excluir de tributação em IRS as mais-valias na venda de um imóvel que era habitação própria e permanente?`
- Expected answer:
  The exclusion depends on reinvesting the realization value net of any acquisition loan amortization in another qualifying property or related construction/improvement, within the legal time windows. The sold property must have been the taxpayer's own permanent home, normally evidenced by fiscal domicile in the prior 12 months, subject to exceptional-circumstances relief. The acquired property must also be allocated to permanent housing within the legal deadline.
- Must-hit points:
  - reinvestment uses sale value net of loan amortization
  - reinvestment timing includes 36 months after sale and 24 months before acquisition/use
  - sold property must have been own permanent home
  - acquired property must also be allocated to permanent housing within the legal deadline
- Source: [Portal das Finanças FAQ 5861](https://info.portaldasfinancas.gov.pt/pt/apoio_contribuinte/questoes_frequentes/pages/faqs-00566.aspx)

### PT-LAW-002

- Domain: `tax`
- Question: `Num caso de reinvestimento para exclusão de mais-valias, é obrigatório declarar a intenção de reinvestir?`
- Expected answer:
  Yes. The taxpayer must declare the intention to reinvest, even if only partial, in Annex G of IRS Model 3 for the year of sale, and later demonstrate the effective reinvestment in that declaration and in the following three years when applicable.
- Must-hit points:
  - intention must be declared
  - partial reinvestment still counts
  - declaration is in Annex G of Modelo 3
  - effective reinvestment may need to be evidenced in later declarations
- Source: [Portal das Finanças FAQ 5861 / 5864 area](https://info.portaldasfinancas.gov.pt/pt/apoio_contribuinte/questoes_frequentes/pages/faqs-00566.aspx)

### PT-LAW-003

- Domain: `tax`
- Question: `O reinvestimento para exclusão de mais-valias pode ser cumulativo entre compra de terreno e despesas de construção?`
- Expected answer:
  Yes. The FAQ says the reinvestment may be cumulative through acquisition of land for construction and the related construction expenses, as long as those costs are properly documented and legally proven.
- Must-hit points:
  - cumulative reinvestment is allowed
  - can combine land acquisition and construction costs
  - costs must be documented and legally proven
- Source: [Portal das Finanças FAQ 5864](https://info.portaldasfinancas.gov.pt/pt/apoio_contribuinte/questoes_frequentes/pages/faqs-00566.aspx)

### PT-LAW-004

- Domain: `tax`
- Question: `As tornas recebidas numa partilha de bens imóveis estão sujeitas a IRS?`
- Expected answer:
  Yes. The tax FAQ treats tornas as gains arising from the onerous transfer of real rights over immovable property, so they are subject to Category G capital-gains taxation, even if the recipient later waives them. The FAQ also says the amount received should be reported in Annex G in the year after the deed of partition.
- Must-hit points:
  - yes, subject to IRS Category G
  - based on onerous transfer of rights over immovable property
  - applies even if the tornas are waived
  - Annex G reporting point
- Source: [Portal das Finanças FAQ 5869](https://info.portaldasfinancas.gov.pt/pt/apoio_contribuinte/questoes_frequentes/pages/faqs-00566.aspx)

### PT-LAW-005

- Domain: `inheritance`
- Question: `O que se pode fazer no Balcão das Heranças?`
- Expected answer:
  The Balcão das Heranças can be used to perform habilitação de herdeiros, partition of the estate, and registration of estate assets. Justiça.gov.pt also states that heirs can be identified and the estate assets can be registered in the name of all heirs in common.
- Must-hit points:
  - habilitação de herdeiros
  - partilha
  - registo dos bens da herança
- Source:
  - [Balcão Heranças | Justiça.gov.pt](https://justica.gov.pt/Servicos/Balcao-Herancas)
  - [Herança | Justiça.gov.pt](https://justica.gov.pt/Registos/Civil/Heranca)

### PT-LAW-006

- Domain: `inheritance`
- Question: `Na habilitação de herdeiros, é possível fazer logo o registo dos bens da herança em nome de todos os herdeiros?`
- Expected answer:
  Yes. Justiça.gov.pt says that when doing habilitação de herdeiros it is possible to register the estate assets in common in the name of all heirs.
- Must-hit points:
  - yes
  - registration can be done together with habilitação
  - in favor of all heirs in common
- Source:
  - [Herança | Justiça.gov.pt](https://justica.gov.pt/Registos/Civil/Heranca)
  - [Guia Espaço Óbito](https://justica.gov.pt/guia-do-espaco-obito/primeira-vinda-ao-espaco-obito)

### PT-LAW-007

- Domain: `driving`
- Question: `Quando é que uma carta de condução pode ser revalidada antes de caducar?`
- Expected answer:
  According to IMT, the revalidation request can be made in the six months before the end of validity, following the age/category rules applicable to the driver.
- Must-hit points:
  - six months before expiry
  - depends on category/age rules
- Source:
  - [IMT FAQ: carta a caducar dentro de alguns meses](https://www.imt-ip.pt/faq/a-minha-carta-de-conducao-vai-caducar-dentro-de-alguns-meses-como-e-onde-posso-revalidar/)
  - [IMT revalidation page](https://www.imt-ip.pt/condutores/informacoes-gerais/quero-ser-condutor/revalidacao-da-carta-de-conducao/)

### PT-LAW-008

- Domain: `driving`
- Question: `Onde pode ser pedido o revalidação da carta de condução?`
- Expected answer:
  IMT says the request can be made through IMT Online, in person at IMT regional or district desks, at Espaço do Cidadão, or through an IMT partner.
- Must-hit points:
  - IMT Online
  - IMT desk / regional or district service
  - Espaço do Cidadão
  - partner channel
- Source: [IMT FAQ: como e onde revalidar](https://www.imt-ip.pt/faq/a-minha-carta-de-conducao-vai-caducar-dentro-de-alguns-meses-como-e-onde-posso-revalidar/)

### PT-LAW-009

- Domain: `driving`
- Question: `Se a carta de condução estiver caducada há mais de 2 anos e menos de 5 anos, o que é normalmente exigido para revalidar?`
- Expected answer:
  IMT states that revalidation in that range is generally conditioned on passing a practical test in a special exam, without needing driving-school enrollment, except for holders of AM, A1, A2, A, B1, B and BE titles who have not yet reached 50 years old.
- Must-hit points:
  - practical test / special exam
  - no ordinary school enrollment needed
  - exception for AM/A1/A2/A/B1/B/BE holders under 50
- Source:
  - [IMT FAQ: carta caducada há mais de 2 anos](https://www.imt-ip.pt/faq/a-minha-carta-de-conducao-esta-caducada-ha-mais-de-2-anos-como-posso-revalidar/)
  - [IMT FAQ listing page](https://www.imt-ip.pt/sites/IMTT/Portugues/PerguntasFrequentes/Veiculos/Paginas/Questao1.aspx)

### PT-LAW-010

- Domain: `driving`
- Question: `Se a carta de condução estiver caducada há mais de 5 anos e menos de 10 anos, o que é normalmente exigido para revalidar?`
- Expected answer:
  IMT says revalidation in that range is conditioned on completing a specific training course successfully and then passing a practical test.
- Must-hit points:
  - specific training course
  - practical test
  - applies to titles expired more than 5 and less than 10 years
- Source:
  - [IMT FAQ: carta caducada há mais de 5 anos](https://www.imt-ip.pt/faq/a-minha-carta-de-conducao-esta-caducada-ha-mais-de-5-anos-como-posso-revalidar/)
  - [IMT titles expired 5 to 10 years](https://www.imt-ip.pt/condutores/obtencao/exame-de-conducao-especial/titulos-caducados-ha-mais-de-5-anos-e-ha-menos-de-10-anos/)

### PT-LAW-011

- Domain: `social_security`
- Question: `Até quando é que um trabalhador independente deve entregar a declaração trimestral à Segurança Social?`
- Expected answer:
  The practical guide says the quarterly declaration must be submitted by the last day of January, April, July and October.
- Must-hit points:
  - quarterly declaration
  - last day of January, April, July, October
- Source:
  - [Guia Prático - Trabalhador Independente](https://www.seg-social.pt/documents/10152/14965/1009%20Trabalhador%20independente%20-%20novo%20regime/87b6e00c-523d-4718-8a88-942ea804c18a)
  - [Segurança Social Direta notice](https://www.seg-social.pt/ptss/pssd/noticias/trabalhadores-independentes-entrega-da-declaracao-trimestral)

### PT-LAW-012

- Domain: `social_security`
- Question: `Um trabalhador independente pode entregar a declaração trimestral fora de prazo?`
- Expected answer:
  Yes. The practical guide says a functionality was made available in Segurança Social Direta allowing the quarterly declaration to be submitted late, starting on the first day after the end of the normal filing period.
- Must-hit points:
  - yes
  - late submission functionality exists
  - starts from the first day after the normal deadline period ends
- Source: [Guia Prático - Trabalhador Independente](https://www.seg-social.pt/documents/10152/15974914/1009%20Trabalhador%20independente%20-%20novo%20regime/87b6e00c-523d-4718-8a88-942ea804c18a)

### PT-LAW-013

- Domain: `parentality`
- Question: `Qual é a duração base do subsídio parental inicial?`
- Expected answer:
  Segurança Social says the initial parental benefit is granted for up to 120 or 150 consecutive days, depending on the parents' choice.
- Must-hit points:
  - 120 or 150 consecutive days
  - depends on parents' option
- Source:
  - [Guia Prático - Subsídio Parental Inicial](https://www.seg-social.pt/documents/10152/14973/3010_subs%C3%ADdio_parental/f724beed-a5cb-4239-8fcc-fa09d7a6900f)
  - [Parental benefit - Segurança Social](https://en.seg-social.pt/o-parental-benefit)

### PT-LAW-014

- Domain: `parentality`
- Question: `Quando é que o período do subsídio parental inicial pode aumentar 30 dias?`
- Expected answer:
  The period can increase by 30 days when the parents share the leave and each parent takes leave exclusively for the required minimum blocks after the mother's mandatory initial period.
- Must-hit points:
  - increase is 30 days
  - depends on sharing the leave
  - each parent must take exclusive leave in the required blocks
- Source:
  - [Guia Prático - Subsídio Social Parental Inicial](https://www.seg-social.pt/documents/10152/14519835/subsidio_social_parental.pdf/f6ad637c-a1e3-404d-944c-451048decd59)
  - [Parental benefit - Segurança Social](https://en.seg-social.pt/o-parental-benefit)

### PT-LAW-015

- Domain: `family_support`
- Question: `Quem pode pedir o Fundo de Garantia dos Alimentos Devidos a Menores?`
- Expected answer:
  According to Segurança Social, besides the Ministério Público, the fund may be requested by the person who has custody of the child or young person, acting as legal representative, through a court case near the place where they live against the debtor parent.
- Must-hit points:
  - Ministério Público can request it
  - legal representative / custodian can also request it
  - request is through a court case
  - directed against the debtor parent
- Source: [Fundo de Garantia dos Alimentos Devidos a Menores](https://www.seg-social.pt/ptss/pssd/menu/familia/desenvolvimento-criancas-jovens/fundo-garantia-alimentos-menores)

## Notes

- This is a seed benchmark, not a comprehensive legal exam.
- Several sources are FAQ or practical-guide style summaries from official public bodies, not consolidated statutes.
- For statute-verbatim evaluation, use a separate exact-wording set with article-level sources only.
- The main benchmark score should come from `expand -> persist -> answer`, not from `archive-only`.
- Useful reporting lanes are:
  - `archive_only_diagnostic`
  - `expand_mode_primary`
  - `second_run_local_reuse`
