---
name: domain-archive-pack-builder
description: Use when an archive needs a domain-local operating pack with recipes, eval starters, and an operator skill so future agents can answer safely within that domain
---

# Domain Archive Pack Builder

Generate the domain-pack contract on top of a Ledger archive.

## Rules

- Keep Ledger core generic.
- Generate archive-local recipes, not source-specific framework code.
- Prefer YAML for structured rules and Markdown with frontmatter for human-and-machine operating notes.
- Let the LLM decide the domain shape, but use deterministic scripts to scaffold and validate the pack.
- Domain packs should stay small, inspectable, and easy for future agents to update.
- Treat the pack as a contract for future agents, not as loose metadata.
- Standardize reusable index practices in generated outputs before adding archive-specific glue.
- Put stable bounded-expansion discipline in the pack before relying on operator memory.

## Outputs

Create or update these archive-local files:

- `recipes/domain-profile.yaml`
- `recipes/source-families.yaml`
- `recipes/source-playbooks.yaml`
- `recipes/source-acquisition.yaml`
- `recipes/extract-units.yaml`
- `recipes/persistence-rules.yaml`
- `recipes/fact-intake.yaml`
- `recipes/freshness-rules.yaml`
- `recipes/exception-patterns.yaml`
- `recipes/answer-contract.yaml`
- `recipes/support-hierarchy.yaml`
- `recipes/confirmation-thresholds.yaml`
- `domain/DOMAIN.md`
- `domain/OPERATIONS.md`
- `domain/ENRICHMENT_PROTOCOL.md`
- `domain/coverage-ledger.yaml`
- `domain/expansion-report-template.md`
- `templates/domain-pack/claims.json`
- `templates/domain-pack/answer.json`
- `templates/domain-pack/decision.json`
- `templates/domain-pack/expansion-plan.json`
- `skills/<domain-slug>-operator/SKILL.md`
- `archive-evals/scenarios/*.json`
- `archive-evals/thresholds.json`
- `domain-benchmarks/thresholds.json`

## Workflow

1. Inspect the archive purpose, policy, and existing eval posture.
2. Ask the user only the domain questions that materially affect safety or output shape.
3. Write `recipes/domain-profile.yaml` first.
4. Run `scripts/scaffold_domain_pack.py` to materialize the pack deterministically.
5. Review the generated files and tighten any domain-specific wording that needs human judgment.
6. Add or refine an expansion recipe by editing the generated acquisition, extract, persistence, and coverage files.
7. When the domain needs bounded canonical expansion, express it through question-shape source policy and search budgets in the generated recipe files.
8. Run `scripts/validate_domain_pack.py`.
9. Run `scripts/benchmark_domain_pack.py` when a committed example or fixture exists and compare baseline vs packed behavior.
10. Tell the user what was generated, what the archive now remembers and checks by default, what still needs domain confirmation, and how future agents should use it.

Generated operator skills should make Python entrypoints explicit:

- default to `uv run python scripts/run_archive_check.py ...` for archive checks
- reserve bare `python3` for helper scripts that do not read recipe YAML or depend on project-installed packages
- document the required payload shape for `check_confirmation_boundary`

Read [references/domain-pack-contract.md](references/domain-pack-contract.md) before deciding what belongs in the pack.
Read [references/domain-profile-schema.md](references/domain-profile-schema.md) before writing the profile.
Read [references/generated-pack-outputs.md](references/generated-pack-outputs.md) before changing scaffold outputs.
Read [references/operator-skill-contract.md](references/operator-skill-contract.md) before editing the generated operator skill.
Read [references/source-playbooks.md](references/source-playbooks.md) before inventing new source-shape behavior.
Read [references/expansion-recipes.md](references/expansion-recipes.md) before tightening the generated expansion recipes.

When a canonical source family still needs diagnosis, cheap-first exploration, or browser-escalation judgment, use the repo-local `canonical-source-explorer` skill before freezing pack rules.

## Intake

Settle these questions before generating the pack:

- What is the domain name and short slug?
- What are the canonical source families?
- What should the agent persist as durable archive knowledge?
- When may the agent gather more evidence on its own?
- When must the agent ask the user for more domain detail?
- What confidence posture should final answers follow?
- How volatile is the domain: stable, periodic, annual, or fast-changing?
- Is user fact intake required before safe application?
- Are exceptions and cross-references dense or light?
- Is exact wording critical, important, or low-risk?
- What answer sections must always appear in final responses?

Prefer writing the answers into `recipes/domain-profile.yaml` rather than freeform notes.

## Cross-index practice floor

Every generated archive should receive the same reusable practice layer unless the domain clearly cannot support it:

- archive-memory surfaces for known gaps, provisional weakness, partial topics, and stale topics
- shared judgment points for coverage, support strength, pre-answer weakness, auto-expand policy, and confirmation boundary
- bounded canonical expansion policy for question-shape source selection, refinement, and stopping
- starter proof families for direct answer, expand-then-answer, ask-user, false completion, and replay closure

New domains should usually require new pack data or a new source playbook, not a new theory of archive operation.

## Scripts

Use the bundled deterministic helpers:

- `uv run python skills/domain-archive-pack-builder/scripts/scaffold_domain_pack.py ...`
- `uv run python skills/domain-archive-pack-builder/scripts/validate_domain_pack.py ...`
- `uv run python skills/domain-archive-pack-builder/scripts/check_expansion_plan.py ...`
- `uv run python skills/domain-archive-pack-builder/scripts/check_support_hierarchy.py ...`
- `uv run python skills/domain-archive-pack-builder/scripts/check_confirmation_boundary.py ...`
- `uv run python skills/domain-archive-pack-builder/scripts/benchmark_domain_pack.py ...`

Do not hand-build the entire domain pack when the helper scripts can create the stable structure first.
