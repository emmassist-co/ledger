# Domain Profile Schema

Write the profile at `recipes/domain-profile.yaml`.

Required fields:

- `schema_version`
- `domain_name`
- `domain_slug`
- `domain_summary`
- `risk_class`
- `operating_mode`
- `volatility`
- `fact_sensitivity`
- `exception_density`
- `exact_wording`
- `source_families`
- `required_facts`
- `exception_classes`
- `answer_sections`

The profile is the compact source of truth for the pack contract. It should describe:

- the bounded domain
- the canonical source families and retrieval units
- the persistence and confidence posture the generated recipes should enforce
- the fact sensitivity and answer-shape expectations future agents should follow
- optional question-shape defaults when the domain needs to override the generated bounded-expansion policy

Minimal example:

```yaml
schema_version: 1
domain_name: Portuguese Tax Archive
domain_slug: portuguese-tax-archive
domain_summary: Archive-first pack for Portuguese tax rule lookup and scoped case application.
risk_class: high
operating_mode: accuracy_first
volatility: annual
fact_sensitivity: required
exception_density: high
exact_wording: critical
source_families:
  - name: statutes
    canonical_source_type: official
    retrieval_unit: article
    persistence_default: on_use
required_facts:
  - fact_id: residency
    prompt: Is the taxpayer resident in Portugal for the relevant period?
    required_for:
      - case_application
exception_classes:
  - timing
  - eligibility
answer_sections:
  - rule_found
  - missing_facts
  - evidence_type
  - verified_at
```

Optional bounded-expansion override:

```yaml
question_shapes:
  - name: rule_lookup
    allowed_source_families:
      - statutes
      - official_faqs
    preferred_source_family: statutes
    bounded_search:
      initial_query_budget: 3
      refinement_query_budget: 2
      allow_second_stage_refinement: true
      allow_cross_family_fallback: false
```

Allowed enums:

- `risk_class`: `low`, `medium`, `high`
- `operating_mode`: `speed_first`, `balanced`, `accuracy_first`
- `volatility`: `stable`, `periodic`, `annual`, `fast_changing`
- `fact_sensitivity`: `minimal`, `helpful`, `required`
- `exception_density`: `low`, `medium`, `high`
- `exact_wording`: `low`, `important`, `critical`

Structure requirements:

- Each `source_families` entry must include:
  - `name`
  - `canonical_source_type`
  - `retrieval_unit`
  - `persistence_default`
- Each `required_facts` entry must include:
  - `fact_id`
  - `prompt`
  - `required_for`
- `answer_sections` should be a non-empty list of strings.
- If `question_shapes` is present, each entry must include:
  - `name`
  - `allowed_source_families`
  - `preferred_source_family`
  - `bounded_search`
