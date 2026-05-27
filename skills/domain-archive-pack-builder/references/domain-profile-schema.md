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

Allowed enums:

- `risk_class`: `low`, `medium`, `high`
- `operating_mode`: `speed_first`, `balanced`, `accuracy_first`
- `volatility`: `stable`, `periodic`, `annual`, `fast_changing`
- `fact_sensitivity`: `minimal`, `helpful`, `required`
- `exception_density`: `low`, `medium`, `high`
- `exact_wording`: `low`, `important`, `critical`
