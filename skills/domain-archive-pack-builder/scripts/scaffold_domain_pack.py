from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


REQUIRED_PROFILE_KEYS = {
    "schema_version",
    "domain_name",
    "domain_slug",
    "domain_summary",
    "risk_class",
    "operating_mode",
    "volatility",
    "fact_sensitivity",
    "exception_density",
    "exact_wording",
    "source_families",
    "required_facts",
    "exception_classes",
    "answer_sections",
}

OPTIONAL_PROFILE_KEYS = {
    "question_shapes",
}

REQUIRED_SOURCE_FAMILY_KEYS = {
    "name",
    "canonical_source_type",
    "retrieval_unit",
    "persistence_default",
}

REQUIRED_FACT_KEYS = {
    "fact_id",
    "prompt",
    "required_for",
}

ALLOWED_ENUMS = {
    "risk_class": {"low", "medium", "high"},
    "operating_mode": {"speed_first", "balanced", "accuracy_first"},
    "volatility": {"stable", "periodic", "annual", "fast_changing"},
    "fact_sensitivity": {"minimal", "helpful", "required"},
    "exception_density": {"low", "medium", "high"},
    "exact_wording": {"low", "important", "critical"},
}

REQUIRED_QUESTION_SHAPE_KEYS = {
    "name",
    "allowed_source_families",
    "preferred_source_family",
    "bounded_search",
}

REQUIRED_BOUNDED_SEARCH_KEYS = {
    "initial_query_budget",
    "refinement_query_budget",
    "allow_second_stage_refinement",
    "allow_cross_family_fallback",
}


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def dump_yaml(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def validate_profile(profile: dict) -> list[str]:
    failures = []
    missing = sorted(REQUIRED_PROFILE_KEYS - set(profile))
    if missing:
        failures.append(f"missing required keys: {', '.join(missing)}")
    for key, allowed in ALLOWED_ENUMS.items():
        value = profile.get(key)
        if value is not None and value not in allowed:
            failures.append(f"{key} must be one of: {', '.join(sorted(allowed))}")
    source_families = profile.get("source_families")
    if not isinstance(source_families, list) or not source_families:
        failures.append("source_families must be a non-empty list")
    elif not all(isinstance(family, dict) for family in source_families):
        failures.append("source_families entries must be objects")
    else:
        for index, family in enumerate(source_families):
            missing_family = sorted(REQUIRED_SOURCE_FAMILY_KEYS - set(family))
            if missing_family:
                failures.append(
                    f"source_families[{index}] missing required keys: {', '.join(missing_family)}"
                )
    family_names = [family.get("name") for family in source_families or [] if isinstance(family, dict)]
    required_facts = profile.get("required_facts")
    if not isinstance(required_facts, list):
        failures.append("required_facts must be a list")
    elif not all(isinstance(fact, dict) for fact in required_facts):
        failures.append("required_facts entries must be objects")
    else:
        for index, fact in enumerate(required_facts):
            missing_fact = sorted(REQUIRED_FACT_KEYS - set(fact))
            if missing_fact:
                failures.append(
                    f"required_facts[{index}] missing required keys: {', '.join(missing_fact)}"
                )
            required_for = fact.get("required_for")
            if not isinstance(required_for, list) or not required_for:
                failures.append(f"required_facts[{index}].required_for must be a non-empty list")
    if not isinstance(profile.get("exception_classes"), list):
        failures.append("exception_classes must be a list")
    answer_sections = profile.get("answer_sections")
    if not isinstance(answer_sections, list) or not answer_sections:
        failures.append("answer_sections must be a non-empty list")
    elif not all(isinstance(section, str) and section.strip() for section in answer_sections):
        failures.append("answer_sections entries must be non-empty strings")
    question_shapes = profile.get("question_shapes")
    if question_shapes is not None:
        if not isinstance(question_shapes, list) or not question_shapes:
            failures.append("question_shapes must be a non-empty list when provided")
        elif not all(isinstance(shape, dict) for shape in question_shapes):
            failures.append("question_shapes entries must be objects")
        else:
            for index, shape in enumerate(question_shapes):
                missing_shape = sorted(REQUIRED_QUESTION_SHAPE_KEYS - set(shape))
                if missing_shape:
                    failures.append(
                        f"question_shapes[{index}] missing required keys: {', '.join(missing_shape)}"
                    )
                    continue
                allowed = shape.get("allowed_source_families")
                if not isinstance(allowed, list) or not allowed or not all(isinstance(item, str) and item.strip() for item in allowed):
                    failures.append(f"question_shapes[{index}].allowed_source_families must be a non-empty list of strings")
                else:
                    unknown = [item for item in allowed if item not in family_names]
                    if unknown:
                        failures.append(
                            f"question_shapes[{index}].allowed_source_families contains unknown families: {', '.join(unknown)}"
                        )
                preferred = shape.get("preferred_source_family")
                if not isinstance(preferred, str) or not preferred.strip():
                    failures.append(f"question_shapes[{index}].preferred_source_family must be a non-empty string")
                elif isinstance(allowed, list) and preferred not in allowed:
                    failures.append(
                        f"question_shapes[{index}].preferred_source_family must be a member of allowed_source_families"
                    )
                bounded_search = shape.get("bounded_search")
                if not isinstance(bounded_search, dict):
                    failures.append(f"question_shapes[{index}].bounded_search must be an object")
                else:
                    missing_bounded = sorted(REQUIRED_BOUNDED_SEARCH_KEYS - set(bounded_search))
                    if missing_bounded:
                        failures.append(
                            f"question_shapes[{index}].bounded_search missing required keys: {', '.join(missing_bounded)}"
                        )
                    for numeric_key in ("initial_query_budget", "refinement_query_budget"):
                        value = bounded_search.get(numeric_key)
                        if not isinstance(value, int) or value < 0:
                            failures.append(
                                f"question_shapes[{index}].bounded_search.{numeric_key} must be a non-negative integer"
                            )
    return failures


def default_question_shapes(profile: dict) -> list[dict]:
    families = [family["name"] for family in profile["source_families"]]
    article_like = [
        family["name"]
        for family in profile["source_families"]
        if family["retrieval_unit"] in {"article", "section"}
    ]
    procedure_like = [
        family["name"]
        for family in profile["source_families"]
        if family["retrieval_unit"] not in {"article", "section"}
    ]
    legal_preferred = article_like[0] if article_like else families[0]
    procedure_allowed = procedure_like or families
    procedure_preferred = procedure_allowed[0]
    return [
        {
            "name": "rule_lookup",
            "allowed_source_families": families,
            "preferred_source_family": legal_preferred,
            "bounded_search": {
                "initial_query_budget": 3,
                "refinement_query_budget": 2,
                "allow_second_stage_refinement": True,
                "allow_cross_family_fallback": False,
            },
        },
        {
            "name": "exact_wording",
            "allowed_source_families": article_like or families,
            "preferred_source_family": legal_preferred,
            "bounded_search": {
                "initial_query_budget": 3,
                "refinement_query_budget": 2,
                "allow_second_stage_refinement": True,
                "allow_cross_family_fallback": False,
            },
        },
        {
            "name": "exception_lookup",
            "allowed_source_families": families,
            "preferred_source_family": legal_preferred,
            "bounded_search": {
                "initial_query_budget": 3,
                "refinement_query_budget": 2,
                "allow_second_stage_refinement": True,
                "allow_cross_family_fallback": False,
            },
        },
        {
            "name": "procedure_lookup",
            "allowed_source_families": procedure_allowed,
            "preferred_source_family": procedure_preferred,
            "bounded_search": {
                "initial_query_budget": 3,
                "refinement_query_budget": 2,
                "allow_second_stage_refinement": True,
                "allow_cross_family_fallback": False,
            },
        },
        {
            "name": "case_application",
            "allowed_source_families": families,
            "preferred_source_family": legal_preferred,
            "bounded_search": {
                "initial_query_budget": 3,
                "refinement_query_budget": 2,
                "allow_second_stage_refinement": True,
                "allow_cross_family_fallback": False,
            },
        },
    ]


def domain_markdown(profile: dict) -> str:
    frontmatter = {
        "domain_name": profile["domain_name"],
        "domain_slug": profile["domain_slug"],
        "risk_class": profile["risk_class"],
        "operating_mode": profile["operating_mode"],
        "volatility": profile["volatility"],
        "fact_sensitivity": profile["fact_sensitivity"],
        "exception_density": profile["exception_density"],
        "exact_wording": profile["exact_wording"],
    }
    lines = ["---", yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=False).strip(), "---", ""]
    lines.extend(
        [
            f"# {profile['domain_name']}",
            "",
            profile["domain_summary"],
            "",
            "## Canonical Source Families",
            "",
        ]
    )
    for family in profile["source_families"]:
        lines.append(
            f"- `{family['name']}`: `{family['canonical_source_type']}` / retrieval unit `{family['retrieval_unit']}`"
        )
    lines.extend(["", "## Required Answer Sections", ""])
    for section in profile["answer_sections"]:
        lines.append(f"- `{section}`")
    lines.extend(["", "## Question Shapes", ""])
    for shape in profile.get("question_shapes", default_question_shapes(profile)):
        lines.append(
            f"- `{shape['name']}`: allowed `{', '.join(shape['allowed_source_families'])}`, preferred `{shape['preferred_source_family']}`"
        )
    return "\n".join(lines) + "\n"


def refresh_before_answer(profile: dict) -> bool:
    return profile["volatility"] in {"annual", "fast_changing"}


def operations_markdown(profile: dict) -> str:
    fact_mode = profile["fact_sensitivity"]
    refresh_required = refresh_before_answer(profile)
    return f"""# Archive Operations

Use this file as the compact operator loop for `{profile['domain_slug']}`.

## Default loop

1. Query the local archive first.
2. Classify the request as `rule_lookup` or `case_application`.
3. Check `domain/coverage-ledger.yaml` before claiming broad coverage or a negative result.
4. Run `uv run python scripts/run_archive_check.py check_coverage_state --archive-root . --term "..." --task-type ...` when a topic may be only partially covered.
5. If support is weak but the topic is in-bounds, follow `domain/ENRICHMENT_PROTOCOL.md` and stay inside the question shape's allowed source families.
6. If an in-bounds `expand` decision reveals a new likely weak slice, register it with `uv run python scripts/run_archive_check.py register_provisional_weak_slice ...`.
7. Persist reusable canonical material rather than one-off case application notes.
8. Re-check freshness before final output.
9. Apply the answer contract before returning the final answer.

## Ask-vs-fetch boundary

- Fetch more evidence on your own when the domain is in-bounds and the missing problem is source coverage.
- Ask the user when the missing problem is domain detail needed for a confident answer.
- Treat `check_coverage_state` failures as a default expansion signal unless the blocker is user facts.
- Use the question shape's allowed and preferred source families before broadening search.
- Current fact posture: `{fact_mode}`.

## Confidence posture

- Treat decisive claims according to `recipes/support-hierarchy.yaml`.
- Treat exact wording as `{profile['exact_wording']}` risk.
- Treat confirmation language according to `recipes/confirmation-thresholds.yaml`.

## Freshness posture

- Refresh required before answer: `{str(refresh_required).lower()}`.
- Follow `recipes/freshness-rules.yaml` when the topic is time-sensitive or version-sensitive.

## Payload templates

- `templates/domain-pack/claims.json` for support checks
- `templates/domain-pack/answer.json` for confirmation-boundary checks
- `templates/domain-pack/decision.json` for answer/expand/persist decisions
- `templates/domain-pack/expansion-plan.json` for expansion-plan checks
"""


def enrichment_protocol_markdown(profile: dict) -> str:
    return f"""# Enrichment Protocol

Use this protocol when a real question is not fully answered by the local archive.

## Step 1: Classify the question

- Mark it as `rule_lookup` when the user mainly needs the rule.
- Mark it as `case_application` when the user needs the rule applied to provided facts.

## Step 2: Check local support

- Query the archive first.
- Check `domain/coverage-ledger.yaml`.
- Run `check_coverage_state` when the question may sit on a partial topic or known support gap.
- Use `templates/domain-pack/claims.json` if you need to validate decisive support.

## Step 3: Decide fetch vs ask-user

- If the topic is in-bounds and the missing problem is source coverage, expand.
- If `check_coverage_state` reports a matched support gap or partial topic, treat that as source coverage weakness by default.
- If the domain pack says `auto_expand_when_below_target`, do not stop at a direct answer while that gap remains.
- If the topic is weak for the first time and you are expanding because of local insufficiency, register a provisional weak slice so the archive remembers the suspicion next time.
- If the missing problem is user/domain facts needed for confidence, ask the user.
- Record the decision with `templates/domain-pack/decision.json`.

## Step 4: Expansion path

1. Start from `recipes/source-families.yaml`.
2. Use `recipes/source-playbooks.yaml` to choose the generic source-shape behavior.
3. Fill `templates/domain-pack/expansion-plan.json`.
4. Keep the first search pass inside the question shape's preferred source family and query budget.
5. If the first pass is weak, allow one bounded refinement stage in the same source family.
6. Validate the expansion plan before fetching.
7. Persist reusable canonical material rather than temporary case notes.
8. After enrichment, resolve any matching provisional weak slice with `resolve_provisional_weak_slice` as `confirmed`, `cleared`, or `superseded`.

## Step 5: Reassess before answering

- Re-check support hierarchy for decisive claims.
- Re-check confirmation thresholds for user-facing conclusions.
- Re-check freshness when the topic is time-sensitive.
- Distinguish `provisional` from `at_target` answer quality before stopping.
- If the answer is still provisional because of a known support gap, record `follow_up_action: expand`.
- Follow the answer contract before final output.

## Stop conditions

- Stop and ask the user when confidence is blocked by missing facts.
- Stop and downgrade the answer when support remains too weak after allowed expansion.
- Stop boundedly after the question shape's refinement budget instead of silently widening to another source family.
- If the archive can answer cautiously but remains below target quality, answer provisionally and record follow-up enrichment instead of pretending the archive is done.
- Stop and avoid generic web search when the missing slice is still in a known canonical path.
"""


def operator_skill_markdown(profile: dict) -> str:
    skill_name = f"{profile['domain_slug']}-operator"
    description = (
        f"Use when answering or enriching {profile['domain_name']} questions with this archive, "
        "especially when facts, exceptions, freshness, or exact wording affect safety"
    )
    fact_mode = profile["fact_sensitivity"]
    exact = profile["exact_wording"]
    return f"""---
name: {skill_name}
description: {description}
---

# {profile['domain_name']} Operator

Use the local archive first, then the generated recipes.

## Required Reads

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
- `domain/coverage-ledger.yaml`
- `domain/DOMAIN.md`
- `domain/OPERATIONS.md`
- `domain/ENRICHMENT_PROTOCOL.md`
- `templates/domain-pack/claims.json`
- `uv run python scripts/run_archive_check.py check_coverage_state --archive-root . --term "..."`
- `templates/domain-pack/answer.json`
- `templates/domain-pack/decision.json`
- `uv run python scripts/run_archive_check.py register_provisional_weak_slice --archive-root . --term "..."`
- `uv run python scripts/run_archive_check.py resolve_provisional_weak_slice --archive-root . --term "..." --resolution confirmed`
- `templates/domain-pack/expansion-plan.json`

## Workflow

1. Query the archive first.
2. Classify the request as `rule_lookup` or `case_application`.
3. Check the coverage ledger before claiming broad coverage or a negative result.
4. Read `domain/OPERATIONS.md` before ad hoc expansion or case application.
5. Read `domain/ENRICHMENT_PROTOCOL.md` when local support is weak.
6. Use `uv run python scripts/run_archive_check.py check_coverage_state ...` when a topic may be partial even if retrieval found something.
7. Use `uv run python scripts/run_archive_check.py ...` for archive and domain-pack checks by default, especially when a check needs JSON payloads or reads recipe files.
8. If the answer needs expansion, write an expansion plan and validate it before fetching.
9. Keep expansion inside the question shape's allowed source families and start with the preferred one.
10. Allow only one bounded refinement pass inside the same source family unless the pack says otherwise.
11. Check freshness before answering when the topic is time-sensitive.
12. Check required facts before case application.
13. Check exception patterns before treating a base rule as complete.
14. Treat exact wording as `{exact}` risk.
15. Use the support hierarchy to label decisive claims as `raw_source`, `extract`, or `derived_summary`.
16. Use the confirmation thresholds before saying a person is confirmed eligible, ineligible, or otherwise settled on provided facts.
17. Follow the answer contract before final output.

## Rules

- Do not turn a covered rule lookup into case application without the fact-intake checks.
- Do not present paraphrase as exact wording when the answer contract requires stronger support.
- If facts are `{fact_mode}`, say so explicitly when they are missing.
- Use `recipes/source-acquisition.yaml`, `recipes/extract-units.yaml`, and `recipes/persistence-rules.yaml` to decide what source unit to save and what artifact to materialize.
- Use `recipes/source-playbooks.yaml` to understand the generic source-shape before inventing source-specific navigation behavior.
- Use the question-shape policy in `recipes/source-acquisition.yaml` before choosing or broadening a source family.
- Use `recipes/support-hierarchy.yaml` to decide whether decisive claims are strong enough for the current answer.
- Use `recipes/confirmation-thresholds.yaml` to avoid presenting plausible case applications as confirmed outcomes too early.
- Use `check_coverage_state` to detect known partial topics and support gaps before treating a found artifact as sufficient.
- When `recipes/answer-contract.yaml` sets `auto_expand_when_below_target: true`, treat `expand` as the default next action for known support gaps unless missing user facts are the real blocker.
- When a fresh `expand` decision exposes likely below-target support, register a provisional weak slice instead of relying on memory or ad hoc notes.
- After later enrichment, resolve that provisional weak slice as `confirmed`, `cleared`, or `superseded` so the ledger does not accumulate stale suspicion.
- Use the starter payloads under `templates/domain-pack/` when preparing helper-check JSON.
- Use `templates/domain-pack/decision.json` to record whether the next step is `answer`, `expand`, `persist`, or `ask_user`.
- Prefer `uv run python scripts/run_archive_check.py ...` over raw verifier invocations when passing `claims`, `decision`, `plan`, or `answer` payloads.
- Use bare `python3` only for simple helper calls that do not depend on recipe YAML or project-installed packages.
- Treat `check_support_hierarchy`, `check_confirmation_boundary`, and `check_expansion_plan` as `uv run python` commands.
- For `check_confirmation_boundary`, pass the archive's expected fields explicitly: `conclusion_level`, `blocking_facts_confirmed`, `blocking_facts_missing`, and `phrasing`.
- Validate expansion plans before growth steps that add durable knowledge.
- If local support is not strong enough for a concrete rule effect but the official source family is known, say that expansion is the next step.
- Prefer archive expansion over generic web search when the missing slice is in-bounds and canonical.
- Treat bounded failure on the correct source family as better than a plausible answer from the wrong source family.
"""


def build_source_families(profile: dict) -> dict:
    return {
        "schema_version": 1,
        "domain_slug": profile["domain_slug"],
        "source_families": profile["source_families"],
    }


def playbook_type_for_family(family: dict) -> str:
    retrieval_unit = family["retrieval_unit"]
    source_type = family["canonical_source_type"]
    if retrieval_unit in {"article", "section"}:
        return f"{source_type}_article_source"
    if retrieval_unit == "faq_entry":
        return f"{source_type}_faq_source"
    if retrieval_unit in {"annual_table", "rate_table"}:
        return f"{source_type}_annual_table_source"
    if retrieval_unit in {"registry_entry", "record"}:
        return f"{source_type}_registry_source"
    return f"{source_type}_document_source"


def navigation_steps_for_family(family: dict) -> list[str]:
    retrieval_unit = family["retrieval_unit"]
    if retrieval_unit in {"article", "section"}:
        return [
            "resolve canonical act or page",
            "navigate to the target article or section",
            "preserve raw source before paraphrase",
        ]
    if retrieval_unit == "faq_entry":
        return [
            "resolve the official FAQ page",
            "target the relevant entry",
            "persist the entry when reusable",
        ]
    if retrieval_unit in {"annual_table", "rate_table"}:
        return [
            "resolve the official table for the relevant period",
            "capture the exact row or value block",
            "record verified_at for future reuse",
        ]
    return [
        "resolve the official canonical page",
        "navigate to the relevant unit",
        "persist reusable canonical material",
    ]


def build_source_playbooks(profile: dict) -> dict:
    playbooks = []
    question_shapes = profile.get("question_shapes", default_question_shapes(profile))
    for family in profile["source_families"]:
        retrieval_unit = family["retrieval_unit"]
        search_guidance = {}
        for shape in question_shapes:
            if family["name"] not in shape["allowed_source_families"]:
                continue
            if retrieval_unit in {"article", "section"}:
                templates = [
                    "canonical act or page title plus article or section number",
                    "canonical act title plus decisive rule term",
                ]
            elif retrieval_unit == "faq_entry":
                templates = [
                    "official FAQ page title plus question term",
                    "official FAQ page title plus exception term",
                ]
            else:
                templates = [
                    "canonical page title plus target unit label",
                    "canonical page title plus narrow domain term",
                ]
            search_guidance[shape["name"]] = {
                "query_templates": templates,
                "preferred": shape["preferred_source_family"] == family["name"],
            }
        playbooks.append(
            {
                "source_family": family["name"],
                "playbook_type": playbook_type_for_family(family),
                "retrieval_unit": retrieval_unit,
                "navigation_steps": navigation_steps_for_family(family),
                "persistence_expectation": family["persistence_default"],
                "exact_wording_default": retrieval_unit in {"article", "section"},
                "question_shape_search_guidance": search_guidance,
            }
        )
    return {
        "schema_version": 1,
        "domain_slug": profile["domain_slug"],
        "playbooks": playbooks,
    }


def build_source_acquisition(profile: dict) -> dict:
    question_shapes = profile.get("question_shapes", default_question_shapes(profile))
    return {
        "schema_version": 1,
        "domain_slug": profile["domain_slug"],
        "acquisition_defaults": {
            "official_source_capture_mode": "on_use",
            "persist_raw_by_default": True,
            "require_source_hash": True,
            "require_verified_at": profile["volatility"] in {"periodic", "annual", "fast_changing"}
            or profile["risk_class"] == "high",
        },
        "allowed_source_families": [family["name"] for family in profile["source_families"]],
        "question_shape_policies": question_shapes,
        "skip_persist_reasons": [
            "duplicate",
            "transient_page",
            "out_of_scope",
            "user_specific",
            "insufficient_value",
            "policy_blocked",
        ],
    }


def build_extract_units(profile: dict) -> dict:
    units = []
    for family in profile["source_families"]:
        retrieval_unit = family["retrieval_unit"]
        units.append(
            {
                "source_family": family["name"],
                "retrieval_unit": retrieval_unit,
                "materialize_as": "extract" if retrieval_unit in {"article", "section", "faq_entry"} else "derived_summary",
                "exact_wording_preferred": retrieval_unit in {"article", "section"},
            }
        )
    return {
        "schema_version": 1,
        "domain_slug": profile["domain_slug"],
        "units": units,
    }


def build_persistence_rules(profile: dict) -> dict:
    return {
        "schema_version": 1,
        "domain_slug": profile["domain_slug"],
        "persist_when": [
            "canonical",
            "reusable",
            "general",
            "likely_to_be_asked_again",
        ],
        "prefer_atomic_artifacts": True,
        "do_not_persist": [
            "one_off_user_calculation",
            "ad_hoc_case_application",
            "temporary_fact_combination",
        ],
        "exact_wording_requires": "raw_source_or_extract" if profile["exact_wording"] in {"important", "critical"} else "derived_summary_ok",
    }


def build_fact_intake(profile: dict) -> dict:
    return {
        "schema_version": 1,
        "domain_slug": profile["domain_slug"],
        "fact_sensitivity": profile["fact_sensitivity"],
        "required_facts": profile["required_facts"],
        "rule_lookup_policy": "allow_if_missing" if profile["fact_sensitivity"] != "required" else "scope_rule_only",
        "case_application_policy": "block_if_missing" if profile["fact_sensitivity"] == "required" else "warn_if_missing",
    }


def build_freshness_rules(profile: dict) -> dict:
    refresh_required = refresh_before_answer(profile)
    return {
        "schema_version": 1,
        "domain_slug": profile["domain_slug"],
        "volatility": profile["volatility"],
        "refresh_before_answer": refresh_required,
        "require_verified_at_in_answers": refresh_required or profile["risk_class"] == "high",
    }


def build_exception_patterns(profile: dict) -> dict:
    return {
        "schema_version": 1,
        "domain_slug": profile["domain_slug"],
        "exception_density": profile["exception_density"],
        "exception_classes": profile["exception_classes"],
        "require_exception_check_before_case_application": profile["exception_density"] in {"medium", "high"},
    }


def build_answer_contract(profile: dict) -> dict:
    return {
        "schema_version": 1,
        "domain_slug": profile["domain_slug"],
        "risk_class": profile["risk_class"],
        "exact_wording": profile["exact_wording"],
        "answer_sections": profile["answer_sections"],
        "support_targets": {
            "rule_lookup": "extract",
            "case_application": "extract",
            "exact_wording": "raw_source_or_extract",
            "target_quality_if_high_stakes": "expand_then_answer",
        },
        "auto_expand_when_below_target": True,
        "allow_non_expand_actions_when_below_target": [
            "ask_user",
        ],
        "must_declare_output_mode": True,
        "must_declare_evidence_type": True,
        "must_declare_missing_facts": profile["fact_sensitivity"] != "minimal",
        "must_declare_verified_at": profile["volatility"] in {"annual", "fast_changing"} or profile["risk_class"] == "high",
    }


def build_support_hierarchy(profile: dict) -> dict:
    return {
        "schema_version": 1,
        "domain_slug": profile["domain_slug"],
        "support_levels": [
            "raw_source",
            "extract",
            "derived_summary",
        ],
        "decisive_claim_minimum": "extract" if profile["risk_class"] == "high" else "derived_summary",
        "exact_wording_minimum": "raw_source_or_extract",
        "require_support_label_per_decisive_claim": True,
    }


def build_confirmation_thresholds(profile: dict) -> dict:
    blocking_fact_ids = [fact["fact_id"] for fact in profile["required_facts"] if isinstance(fact, dict) and fact.get("fact_id")]
    return {
        "schema_version": 1,
        "domain_slug": profile["domain_slug"],
        "blocking_fact_ids": blocking_fact_ids,
        "allowed_conclusion_levels": [
            "rule_supported",
            "plausibly_applicable",
            "confirmed_from_provided_facts",
        ],
        "confirmed_requires_all_blocking_facts": True,
        "warn_level_for_missing_blocking_facts": "plausibly_applicable",
        "forbidden_phrases_when_blocking_facts_missing": [
            "confirmed eligible",
            "confirmed ineligible",
            "definitely eligible",
            "definitely ineligible",
        ],
    }


def build_coverage_ledger(profile: dict) -> dict:
    return {
        "schema_version": 1,
        "domain_slug": profile["domain_slug"],
        "coverage_status": "seeded",
        "topics": [],
        "provisional_weak_slices": [],
        "partial_topics": [],
        "stale_topics": [],
        "support_gaps": [],
        "source_families_seen": [family["name"] for family in profile["source_families"]],
        "notes": [
            "Update this ledger as the archive grows.",
            "Use provisional_weak_slices for likely below-target support that has not been fully confirmed yet.",
            "Use partial_topics and stale_topics to avoid overclaiming coverage.",
            "Use support_gaps when the archive can answer provisionally but should still be enriched to reach target quality.",
            "Move a provisional weak slice to support_gaps when the weakness is confirmed, clear it when stronger local support proves the suspicion unnecessary, and mark it superseded when a newer slice replaces the old concern.",
            "Suggested provisional_weak_slices entry keys: topic, labels, task_types, suspected_support_gap, current_support, reason, source_family, artifact_ids, notes.",
            "Suggested support_gaps entry keys: topic, labels, task_types, required_support, current_support, quality_status, follow_up_action, source_family, artifact_ids, notes.",
        ],
    }


def support_claims_template() -> dict:
    return {
        "claims": [
            {
                "claim_id": "replace-with-claim-id",
                "decisive": True,
                "support_type": "extract",
            }
        ]
    }


def confirmation_answer_template(profile: dict) -> dict:
    blocking_fact_ids = [fact["fact_id"] for fact in profile["required_facts"]]
    return {
        "conclusion_level": "plausibly_applicable",
        "blocking_facts_confirmed": [],
        "blocking_facts_missing": blocking_fact_ids,
        "phrasing": "Replace with the user-facing conclusion phrasing to validate.",
    }


def decision_record_template() -> dict:
    return {
        "action": "expand",
        "reason": "Replace with why the next step is answer, expand, persist, or ask_user.",
        "source_type": "official",
        "scope_status": "in_bounds",
        "artifact_kind": "reusable",
        "quality_status": "below_target",
        "follow_up_action": "expand",
    }


def expansion_plan_template(profile: dict) -> dict:
    question_shape = profile.get("question_shapes", default_question_shapes(profile))[0]
    first_family = next(
        family for family in profile["source_families"] if family["name"] == question_shape["preferred_source_family"]
    )
    retrieval_unit = first_family["retrieval_unit"]
    return {
        "task_type": "rule_lookup",
        "question_shape": question_shape["name"],
        "source_family": first_family["name"],
        "source_url": "https://replace-with-canonical-source",
        "unit_type": retrieval_unit,
        "materialize_as": "extract" if retrieval_unit in {"article", "section", "faq_entry"} else "derived_summary",
        "persistence_action": "persist",
        "search_stage": "initial",
        "query_terms": ["replace-with-query-1"],
        "reason": "Replace with the concrete reason this expansion is needed.",
        "exact_wording_claim": profile["exact_wording"] in {"important", "critical"},
    }


def expansion_report_markdown(profile: dict) -> str:
    return f"""---
domain_slug: {profile['domain_slug']}
status: draft
---

# Expansion Report

## Summary

- source_family:
- source_url:
- unit_type:
- action:

## Persistence

- raw_saved:
- extract_created:
- derived_artifacts:

## Verification

- verified_at:
- source_hash:
- checks:

## Coverage Update

- topics_added:
- partial_topics_updated:
- stale_topics_updated:
"""


def starter_thresholds(profile: dict) -> dict:
    ndcg_floor = {
        "low": 0.7,
        "medium": 0.8,
        "high": 0.85,
    }[profile["risk_class"]]
    clean_floor = 1.0 if profile["exception_density"] == "low" else 0.75
    drift_cap = 0.0 if clean_floor == 1.0 else 0.25
    return {
        "minimums": {
            "retrieval_metrics.overall.hit_at_k": 1.0,
            "retrieval_metrics.overall.mrr_at_k": 1.0,
            "retrieval_metrics.overall.ndcg_at_k": ndcg_floor,
            "trajectory_metrics.completion_pass_rate": 1.0,
            "trajectory_metrics.clean_pass_rate": clean_floor,
        },
        "maximums": {
            "trajectory_metrics.drift_rate": drift_cap,
        },
        "equals": {
            "common_failure_modes": [],
        },
        "optional_minimums": {
            "replay_metrics.second_run_local_hit_rate": 1.0,
            "false_completion_metrics.guard_success_rate": 1.0,
        },
        "notes": [
            "Starter thresholds generated from the domain profile.",
            "Replay and false-completion minimums are optional until the archive adds scenarios that exercise those proof families.",
            "Tighten after the first baseline run if the archive becomes a committed benchmark fixture.",
        ],
    }


def domain_benchmark_thresholds(profile: dict) -> dict:
    families: dict[str, dict[str, object]] = {
        "answer_contract": {"enabled": True, "minimum_delta": 0.5},
        "support_hierarchy": {"enabled": True, "minimum_delta": 0.5},
        "confirmation_boundary": {"enabled": True, "minimum_delta": 0.5},
        "scope_boundary": {"enabled": True, "minimum_delta": 0.5},
        "expansion": {"enabled": True, "minimum_delta": 0.5},
        "fact_intake": {"enabled": profile["fact_sensitivity"] in {"helpful", "required"}, "minimum_delta": 0.5},
        "freshness": {
            "enabled": profile["volatility"] in {"periodic", "annual", "fast_changing"} or profile["risk_class"] == "high",
            "minimum_delta": 0.5,
        },
        "exact_wording": {"enabled": profile["exact_wording"] in {"important", "critical"}, "minimum_delta": 0.5},
        "exceptions": {"enabled": profile["exception_density"] in {"medium", "high"}, "minimum_delta": 0.5},
    }
    return {
        "schema_version": 1,
        "domain_slug": profile["domain_slug"],
        "families": families,
        "archive_no_regression": {
            "completion_pass_rate": True,
            "clean_pass_rate": True,
        },
    }


def scenario_payloads(profile: dict) -> list[tuple[str, dict]]:
    slug = profile["domain_slug"]
    must_declare_verified_at = profile["volatility"] in {"annual", "fast_changing"} or profile["risk_class"] == "high"
    retrieval = {
        "id": f"{slug}-retrieval-canonical-anchor",
        "bucket": "retrieval",
        "source_kind": "user_seeded",
        "query": f"{profile['domain_name']} canonical source",
        "prompt": f"Use the archive to find the canonical source family for {profile['domain_name']}.",
        "expected_artifacts": ["replace-with-canonical-artifact-id"],
        "expected_constraints": {
            "require_any_artifact_match": True,
            "require_extract_evidence": False,
            "policy_action": "answer",
            "coverage_term": profile["domain_name"],
        },
        "verifier_checks": ["check_coverage", "check_policy"],
        "trajectory_expectations": {
            "required_events": ["archive.query", "archive.retrieve.hit"],
            "max_first_relevant_rank": 2,
            "max_verifier_calls": 2,
            "max_trace_steps": 6,
        },
        "case_metadata": {
            "tier": "golden",
            "criticality": "high",
            "critical_path": True,
            "origin": "user_seeded",
            "failure_class": "canonical_anchor",
            "stale_after_days": 90,
        },
        "answer_expectations": {
            "response_mode": "direct_answer",
            "expected_decision_action": "answer",
            "minimum_quality_status": "at_target",
            "required_answer_sections": profile["answer_sections"],
            "must_declare_missing_facts": False,
            "must_declare_verified_at": must_declare_verified_at,
        },
        "notes": "Replace placeholder artifact ids after the first committed slice exists.",
    }
    scenarios = [("retrieval-canonical-anchor.json", retrieval)]

    if profile["exact_wording"] in {"important", "critical"}:
        scenarios.append(
            (
                "boundary-exact-wording.json",
                {
                    "id": f"{slug}-boundary-exact-wording",
                    "bucket": "boundary",
                    "source_kind": "user_seeded",
                    "query": f"{profile['domain_name']} exact wording",
                    "prompt": "Ask for exact wording and confirm the archive blocks unsafe paraphrase-only support.",
                    "expected_artifacts": ["replace-with-derived-or-extract-artifact-id"],
                    "expected_constraints": {
                        "require_any_artifact_match": True,
                        "require_extract_evidence": False,
                        "policy_action": "answer",
                        "coverage_term": profile["domain_name"],
                    },
                    "verifier_checks": ["check_coverage", "check_policy", "check_exact_wording"],
                    "expected_verifier_outcomes": {"check_exact_wording": False},
                    "trajectory_expectations": {
                        "exact_wording_claim": {
                            "claim_id": f"{slug}-exact-wording-1",
                            "evidence_ids": ["replace-with-derived-or-extract-artifact-id"],
                            "support_kind": "derived_summary",
                        },
                        "required_events": [
                            "archive.query",
                            "archive.retrieve.hit",
                            "verifier.check_exact_wording.blocked",
                        ],
                        "max_first_relevant_rank": 2,
                        "max_verifier_calls": 3,
                        "max_trace_steps": 7,
                    },
                    "case_metadata": {
                        "tier": "golden",
                        "criticality": "critical",
                        "critical_path": True,
                        "origin": "user_seeded",
                        "failure_class": "exact_wording",
                        "stale_after_days": 90,
                    },
                    "answer_expectations": {
                        "response_mode": "safety_block",
                        "minimum_quality_status": "blocked",
                        "required_answer_sections": profile["answer_sections"],
                        "must_declare_missing_facts": False,
                        "must_declare_verified_at": must_declare_verified_at,
                    },
                    "notes": "Replace placeholder artifact ids and support kind after the first slice exists.",
                },
            )
        )

    if profile["fact_sensitivity"] == "required":
        scenarios.append(
            (
                "boundary-missing-facts.json",
                {
                    "id": f"{slug}-boundary-missing-facts",
                    "bucket": "boundary",
                    "source_kind": "user_seeded",
                    "query": f"{profile['domain_name']} missing facts",
                    "prompt": "Attempt case application without enough user facts and confirm the answer contract downgrades safely.",
                    "expected_artifacts": ["replace-with-rule-artifact-id"],
                    "expected_constraints": {
                        "require_any_artifact_match": True,
                        "require_extract_evidence": False,
                        "policy_action": "answer",
                        "coverage_term": profile["domain_name"],
                    },
                    "verifier_checks": ["check_coverage", "check_policy", "check_decision_record"],
                    "trajectory_expectations": {
                        "decision_record": {
                            "action": "answer",
                            "reason": "rule lookup is allowed but case application is blocked pending facts",
                            "source_type": "official",
                            "scope_status": "in_bounds",
                            "artifact_kind": "reusable",
                        },
                        "required_events": [
                            "archive.query",
                            "archive.retrieve.hit",
                            "decision.answer",
                            "verifier.check_decision_record.pass",
                        ],
                        "max_first_relevant_rank": 2,
                        "max_verifier_calls": 3,
                        "max_trace_steps": 7,
                    },
                    "case_metadata": {
                        "tier": "golden",
                        "criticality": "high",
                        "critical_path": True,
                        "origin": "user_seeded",
                        "failure_class": "missing_facts",
                        "stale_after_days": 90,
                    },
                    "answer_expectations": {
                        "response_mode": "answer_with_missing_facts",
                        "expected_decision_action": "answer",
                        "minimum_quality_status": "provisional",
                        "required_answer_sections": profile["answer_sections"],
                        "must_declare_missing_facts": True,
                        "must_declare_verified_at": must_declare_verified_at,
                    },
                    "notes": "Replace placeholder artifact ids after the first slice exists.",
                },
            )
        )

    return scenarios


def scaffold_pack(root: Path, profile: dict) -> dict:
    recipes = root / "recipes"
    dump_yaml(recipes / "domain-profile.yaml", profile)
    dump_yaml(recipes / "source-families.yaml", build_source_families(profile))
    dump_yaml(recipes / "source-playbooks.yaml", build_source_playbooks(profile))
    dump_yaml(recipes / "source-acquisition.yaml", build_source_acquisition(profile))
    dump_yaml(recipes / "extract-units.yaml", build_extract_units(profile))
    dump_yaml(recipes / "persistence-rules.yaml", build_persistence_rules(profile))
    dump_yaml(recipes / "fact-intake.yaml", build_fact_intake(profile))
    dump_yaml(recipes / "freshness-rules.yaml", build_freshness_rules(profile))
    dump_yaml(recipes / "exception-patterns.yaml", build_exception_patterns(profile))
    dump_yaml(recipes / "answer-contract.yaml", build_answer_contract(profile))
    dump_yaml(recipes / "support-hierarchy.yaml", build_support_hierarchy(profile))
    dump_yaml(recipes / "confirmation-thresholds.yaml", build_confirmation_thresholds(profile))

    write_text(root / "domain" / "DOMAIN.md", domain_markdown(profile))
    write_text(root / "domain" / "OPERATIONS.md", operations_markdown(profile))
    write_text(root / "domain" / "ENRICHMENT_PROTOCOL.md", enrichment_protocol_markdown(profile))
    dump_yaml(root / "domain" / "coverage-ledger.yaml", build_coverage_ledger(profile))
    write_text(root / "domain" / "expansion-report-template.md", expansion_report_markdown(profile))
    write_json(root / "templates" / "domain-pack" / "claims.json", support_claims_template())
    write_json(root / "templates" / "domain-pack" / "answer.json", confirmation_answer_template(profile))
    write_json(root / "templates" / "domain-pack" / "decision.json", decision_record_template())
    write_json(root / "templates" / "domain-pack" / "expansion-plan.json", expansion_plan_template(profile))
    operator_dir = root / "skills" / f"{profile['domain_slug']}-operator"
    write_text(operator_dir / "SKILL.md", operator_skill_markdown(profile))

    scenarios_dir = root / "archive-evals" / "scenarios"
    scenarios = scenario_payloads(profile)
    wrote_scenarios = 0
    existing_scenarios = list(scenarios_dir.glob("*.json"))
    if not existing_scenarios:
        for filename, payload in scenarios:
            write_json(scenarios_dir / filename, payload)
            wrote_scenarios += 1

    thresholds_path = root / "archive-evals" / "thresholds.json"
    if not thresholds_path.exists():
        write_json(thresholds_path, starter_thresholds(profile))
    benchmark_thresholds_path = root / "domain-benchmarks" / "thresholds.json"
    if not benchmark_thresholds_path.exists():
        write_json(benchmark_thresholds_path, domain_benchmark_thresholds(profile))

    return {
        "ok": True,
        "domain_slug": profile["domain_slug"],
        "generated": {
            "recipe_files": 12,
            "scenario_count": wrote_scenarios,
            "operator_skill": str((operator_dir / "SKILL.md").relative_to(root)),
            "operations_guide": "domain/OPERATIONS.md",
            "enrichment_protocol": "domain/ENRICHMENT_PROTOCOL.md",
            "helper_templates": [
                "templates/domain-pack/claims.json",
                "templates/domain-pack/answer.json",
                "templates/domain-pack/decision.json",
                "templates/domain-pack/expansion-plan.json",
            ],
            "domain_benchmark_thresholds": str(benchmark_thresholds_path.relative_to(root)),
        },
        "notes": [
            "Starter scenarios are only scaffolded when archive-evals/scenarios is empty."
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive_root")
    parser.add_argument("--profile", help="Path to recipes/domain-profile.yaml", default=None)
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    root = Path(args.archive_root).resolve()
    profile_path = Path(args.profile).resolve() if args.profile else root / "recipes" / "domain-profile.yaml"
    if not profile_path.exists():
        print(json.dumps({"ok": False, "failures": [{"reason": f"missing profile: {profile_path}"}]}, ensure_ascii=True, indent=2))
        return 1
    profile = load_yaml(profile_path)
    failures = validate_profile(profile)
    if failures:
        print(json.dumps({"ok": False, "failures": failures}, ensure_ascii=True, indent=2))
        return 1
    payload = scaffold_pack(root, profile)
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
