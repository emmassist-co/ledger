# Retrieval Confidence And Coverage

Topical answers from the archive should include a retrieval report, not just a conclusion.

## Goal

Help the archive behave like a research system:

- show what was searched
- show how complete the search was
- show whether expansion is needed

## Required Report Fields

Every topical answer should try to state:

- `topic`
- `searched_scope`
- `search_methods`
- `terms_used`
- `candidate_counts`
- `artifacts_opened`
- `parties_with_direct_evidence`
- `parties_without_direct_hits_in_scope`
- `answer_confidence`
- `slice_confidence`
- `corpus_confidence`
- `expansion_recommendation`

## Confidence Types

Keep these distinct:

- `answer_confidence`: how strong the evidence is for the specific claims made
- `slice_confidence`: how complete the search was inside the currently indexed slice
- `corpus_confidence`: how complete the search was relative to the broader corpus

Do not collapse these into one number.

## Negative Claims

Never say:

- a party has no position
- no relevant discussion exists

unless coverage is genuinely broad enough.

Prefer scoped language such as:

- no direct hits were found in the currently indexed slice
- no promoted blocks in scope currently support that claim

## Multi-Strategy Retrieval

When the topic matters, do not rely on a single query phrase.

Use a mix of:

- exact phrase
- spelling variants
- synonyms or neighboring concepts
- registry-level search
- block-level search

Convergence across multiple strategies raises confidence.

## Expansion Triggers

Recommend expansion when:

- direct hits are sparse
- party coverage is uneven
- only one retrieval strategy produced results
- adjacent source material exists and has not been checked

## Example Shape

```yaml
topic: inteligencia-artificial
searched_scope:
  corpus: parlamento-dar-i-serie
  legislature: XVII
  session: 1.ª Sessão Legislativa
  coverage_level: partial
search_methods:
  - exact phrase
  - synonym expansion
  - registry search
  - block search
terms_used:
  - inteligência artificial
  - IA
  - automação
  - tecnologia
candidate_counts:
  registry_candidates: 90
  direct_topic_hits: 2
  artifacts_opened: 2
parties_with_direct_evidence:
  - Livre
  - L
parties_without_direct_hits_in_scope:
  - PS
  - PSD
  - CDS-PP
answer_confidence: medium
slice_confidence: medium
corpus_confidence: low
expansion_recommendation: expand current session
```
