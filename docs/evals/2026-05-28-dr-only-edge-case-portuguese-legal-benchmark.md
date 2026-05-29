---
title: "DR-Only Edge-Case Portuguese Legal Benchmark"
type: eval
status: draft
date: 2026-05-28
---

# DR-Only Edge-Case Portuguese Legal Benchmark

This set is intentionally biased **away** from the archive's current comfort zone.

The goal is not to reward local coverage. The goal is to force a cold operator to handle stranger, less Google-like, statute-first questions from the `Diario da Republica`, including odd edge cases, scattered rules, and rules that are easy to answer incorrectly from vibe or folklore.

## Design Rules

- Source family: `DR` only
- Question style: legal rule lookup, not service procedure
- Bias target: unusual or non-obvious rules, not common FAQs
- Coverage target: deliberately broad across labor, civil, leases, road traffic, administrative law, obligations, and family-property rules
- Archive posture: these should mostly require `expand`, not reward current local artifacts

## Default Run Mode

1. ask the question cold
2. query the local archive first
3. if support is weak, expand to `DR` only
4. persist the winning slice
5. answer
6. rerun later and measure whether the same question becomes local

`archive-only` is diagnostic only for this set.

## Suggested Scoring Heuristic

- `pass`: legally correct, hits the must-hit points, and stays inside the cited `DR` rule
- `partial`: broadly right, but misses a condition, scope limit, timing rule, or consequence
- `fail`: cites the wrong legal layer, drifts into procedure/help-page content, or invents a rule not traceable to the cited `DR` source

## Questions

### PT-DR-EDGE-001

- Domain: `labour`
- Question: `Em teletrabalho, o que contam como despesas adicionais para compensacao ao trabalhador se as partes nao tiverem fixado um valor?`
- Expected answer:
  In the absence of a fixed-value agreement, additional expenses include the acquisition of goods or services the worker did not have before the telework agreement, as well as the difference between equivalent current expenses and the worker's expenses in the last month of in-person work.
- Must-hit points:
  - applies when the parties did not agree a fixed amount
  - includes goods or services the worker did not previously have
  - includes comparison with the last month of in-person work
- DR source:
  - [Codigo do Trabalho - artigo 168](https://diariodarepublica.pt/redirect/LinkConsolidacaoAntiga.aspx?consolidacaoId=108165886&consolidacaofragmentoId=73481965)

### PT-DR-EDGE-002

- Domain: `labour`
- Question: `Um trabalhador com estatuto de cuidador informal nao principal tem um direito legal especial a teletrabalho?`
- Expected answer:
  Yes. A worker recognized as a non-principal informal caregiver has the right to work under telework for up to four years, consecutive or interpolated, if the work is compatible and the employer has the necessary means and resources.
- Must-hit points:
  - yes
  - applies to `cuidador informal nao principal`
  - up to `4 years`
  - requires compatibility with the activity and employer resources
- DR source:
  - [Codigo do Trabalho - artigo 166-A](https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2009-34546475-124448627)

### PT-DR-EDGE-003

- Domain: `road_traffic`
- Question: `Se um peao intervier num acidente de transito, tambem pode ser submetido a exame de alcool ou colheita de sangue?`
- Expected answer:
  Yes. Drivers and pedestrians involved in a traffic accident must, if their health allows it, undergo an alcohol test. If that is not possible, a blood sample must be collected for later testing.
- Must-hit points:
  - applies to `peoes`, not only drivers
  - depends on the person's health allowing it
  - if the breath test is not possible, blood collection follows
- DR source:
  - [Codigo da Estrada - artigo 156](https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2013-116041830-116043455)

### PT-DR-EDGE-004

- Domain: `obligations`
- Question: `Num contrato-promessa com sinal, qual e a consequencia base se quem deu o sinal faltar culposamente ao cumprimento, e qual e a consequencia se faltar a outra parte?`
- Expected answer:
  If the party who gave the deposit fails to perform, the other party may keep the deposit. If the default is by the receiving party, the non-defaulting party may demand double the amount delivered, without prejudice to the article's specific alternatives.
- Must-hit points:
  - if the giver defaults, the deposit is lost
  - if the receiver defaults, double is owed
  - answer should stay at the article's base rule, not drift into generic damages folklore
- DR source:
  - [Codigo Civil - artigo 442](https://diariodarepublica.pt/dr/legislacao-consolidada/decreto-lei/1966-34509075-59065106)

### PT-DR-EDGE-005

- Domain: `family_property`
- Question: `Os pais podem vender livremente um imovel a um filho se existirem outros filhos? E quem pode pedir a anulacao se isso nao for respeitado?`
- Expected answer:
  No. Parents and grandparents cannot sell to a child or grandchild without the consent of the other children or grandchildren, subject to judicial substitution where the consent cannot be given or is refused. If the rule is broken, the sale is voidable and the action may be brought by the children or grandchildren who did not consent within one year from knowledge of the contract or the end of incapacity.
- Must-hit points:
  - consent of the other children or grandchildren is required
  - judicial substitution of consent is possible
  - the sale is `anulavel`
  - the one-year challenge period belongs to those who did not consent
- DR source:
  - [Codigo Civil - artigo 877](https://diariodarepublica.pt/dr/legislacao-consolidada/decreto-lei/1966-34509075-49858275)

### PT-DR-EDGE-006

- Domain: `family_support`
- Question: `Na ordem legal da obrigacao de alimentos, quem vem antes: irmaos, tios, ou padrasto/madrasta?`
- Expected answer:
  The order is: spouse or ex-spouse, descendants, ascendants, brothers and sisters, uncles and aunts during the minor's minority, and only then stepfather or stepmother in relation to minor stepchildren who were at the spouse's charge.
- Must-hit points:
  - siblings come before uncles/aunts
  - uncles/aunts appear only during the minor's minority
  - stepfather/stepmother appear after that, in the specific minor-stepchild situation
- DR source:
  - [Codigo Civil - artigo 2009](https://diariodarepublica.pt/dr/legislacao-consolidada/decreto-lei/1966-34509075-58403646)

### PT-DR-EDGE-007

- Domain: `civil_liability`
- Question: `Se um animal de companhia sofrer uma lesao de que resulte morte ou afetação grave e permanente da locomocao, o proprietario pode pedir indemnizacao pelo seu proprio sofrimento moral?`
- Expected answer:
  Yes. In the case of injury to a companion animal causing death, loss of an important organ or limb, or serious and permanent impairment of locomotion, the owner may claim adequate compensation for grief or moral suffering under the article's rule.
- Must-hit points:
  - yes
  - covers death, major organ/member loss, or grave and permanent locomotion impairment
  - compensation is for the owner's own grief or moral suffering
- DR source:
  - [Codigo Civil - responsabilidade por lesao de animal de companhia](https://diariodarepublica.pt/dr/legislacao-consolidada/decreto-lei/1966-34509075-49809875)

### PT-DR-EDGE-008

- Domain: `family_property`
- Question: `Num regime de comunhao, os animais de companhia que cada conjuge ja tinha antes do casamento entram automaticamente na comunhao?`
- Expected answer:
  No. Companion animals that each spouse already had at the time of marriage are expressly excluded from the community.
- Must-hit points:
  - no
  - applies to companion animals already held at the time of marriage
  - answer should frame this as an express incomunicability rule
- DR source:
  - [Codigo Civil - artigo 1733](https://diariodarepublica.pt/dr/legislacao-consolidada/decreto-lei/1966-34509075-106549740)

### PT-DR-EDGE-009

- Domain: `property`
- Question: `Sem registo do titulo nem da mera posse, qual e o prazo legal de usucapiao de imoveis em boa fe e em ma fe?`
- Expected answer:
  In the absence of registration of title and of mere possession, usucaption of immovables can occur only after fifteen years in good faith and twenty years in bad faith.
- Must-hit points:
  - no title registration and no possession registration
  - `15 years` in good faith
  - `20 years` in bad faith
- DR source:
  - [Codigo Civil - artigo 1296](https://diariodarepublica.pt/dr/legislacao-consolidada/decreto-lei/1966-34509075-49908775)

### PT-DR-EDGE-010

- Domain: `leases`
- Question: `Num arrendamento habitacional com prazo certo e renovacao automatica, se o prazo inicial for inferior a tres anos, por quanto tempo se renova em regra?`
- Expected answer:
  It renews automatically for successive periods of equal duration or for three years if the original duration is shorter.
- Must-hit points:
  - answer must mention automatic renewal
  - if the original duration is under three years, the renewal period is `3 years`
  - should not confuse this with denunciation by the tenant
- DR source:
  - [NRAU - artigo 1096](https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2006-34578375-45355875)

### PT-DR-EDGE-011

- Domain: `administrative_law`
- Question: `Um ato administrativo com erro material manifesto ou erro de calculo pode ser retificado muito tempo depois, ou existe uma janela curta para isso?`
- Expected answer:
  It can be rectified at any time, as long as the issue is a manifest calculation error or a manifest material error in the expression of the administrative body's will, and the rectification is made by the body competent to revoke the act.
- Must-hit points:
  - `a todo o tempo`
  - only for manifest calculation/material errors
  - competence belongs to the body competent to revoke the act
- DR source:
  - [Retificacao de atos administrativos - artigo 174 do CPA](https://diariodarepublica.pt/dr/lexionario/termo/retificacao-atos-administrativos)

### PT-DR-EDGE-012

- Domain: `leases`
- Question: `Num contrato de arrendamento com prazo certo, o senhorio pode opor-se a renovacao com que antecedencia minima se o prazo inicial ou de renovacao for entre um e seis anos?`
- Expected answer:
  The landlord may oppose automatic renewal with at least 120 days' notice when the initial term or renewal term is equal to or greater than one year and less than six years.
- Must-hit points:
  - opposition to renewal by the landlord
  - `120 days`
  - applies to term `>= 1 year` and `< 6 years`
- DR source:
  - [NRAU - artigo 1097](https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2006-34578375-45355875)

## Notes

- This set is intentionally stranger than the first DR-only benchmark.
- Several questions are designed to catch source drift, overconfident paraphrase, or lazy substitution of common-sense answers for article-level rules.
- If a model does well on this set in `DR-only expand mode`, that is a much stronger signal than doing well on common consumer-law FAQs.
