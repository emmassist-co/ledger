from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from scaffold_domain_pack import currentness_enabled, validate_profile


REQUIRED_RECIPE_FILES = [
    "recipes/domain-profile.yaml",
    "recipes/source-families.yaml",
    "recipes/source-playbooks.yaml",
    "recipes/source-discovery.yaml",
    "recipes/source-acquisition.yaml",
    "recipes/extract-units.yaml",
    "recipes/persistence-rules.yaml",
    "recipes/fact-intake.yaml",
    "recipes/freshness-rules.yaml",
    "recipes/exception-patterns.yaml",
    "recipes/answer-contract.yaml",
    "recipes/support-hierarchy.yaml",
    "recipes/confirmation-thresholds.yaml",
    "domain/DOMAIN.md",
    "domain/OPERATIONS.md",
    "domain/ENRICHMENT_PROTOCOL.md",
    "domain/operator-contract.yaml",
    "domain/coverage-ledger.yaml",
    "domain/expansion-report-template.md",
    "templates/domain-pack/claims.json",
    "templates/domain-pack/answer.json",
    "templates/domain-pack/decision.json",
    "templates/domain-pack/expansion-plan.json",
    "archive-evals/thresholds.json",
    "domain-benchmarks/thresholds.json",
]


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def emit(payload: dict) -> int:
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if payload.get("ok") else 1


def validate_pack(root: Path) -> dict:
    failures = []
    for relative in REQUIRED_RECIPE_FILES:
        if not (root / relative).exists():
            failures.append({"path": relative, "reason": "missing required file"})

    profile_path = root / "recipes" / "domain-profile.yaml"
    profile = load_yaml(profile_path) if profile_path.exists() else {}
    domain_slug = str(profile.get("domain_slug", "")).strip()
    if not domain_slug:
        failures.append({"path": "recipes/domain-profile.yaml", "reason": "missing domain_slug"})
    elif profile_path.exists():
        for failure in validate_profile(profile):
            failures.append({"path": "recipes/domain-profile.yaml", "reason": failure})
    if currentness_enabled(profile):
        for relative in (
            "recipes/currentness-rules.yaml",
            "templates/domain-pack/currentness.json",
        ):
            if not (root / relative).exists():
                failures.append({"path": relative, "reason": "missing currentness file"})

    operator_path = root / "skills" / f"{domain_slug}-operator" / "SKILL.md" if domain_slug else None
    if operator_path and not operator_path.exists():
        failures.append({"path": str(operator_path.relative_to(root)), "reason": "missing operator skill"})

    if operator_path and operator_path.exists():
        skill_text = operator_path.read_text(encoding="utf-8")
        if "domain/operator-contract.yaml" not in skill_text:
            failures.append({"path": str(operator_path.relative_to(root)), "reason": "missing operator contract reference: domain/operator-contract.yaml"})

    operator_contract_path = root / "domain" / "operator-contract.yaml"
    if operator_contract_path.exists():
        contract = load_yaml(operator_contract_path)
        required_reads = contract.get("required_reads")
        if not isinstance(required_reads, list) or not required_reads:
            failures.append({"path": "domain/operator-contract.yaml", "reason": "required_reads must be a non-empty list"})
        else:
            for entry in (
                "recipes/source-families.yaml",
                "recipes/source-playbooks.yaml",
                "recipes/source-discovery.yaml",
                "recipes/source-acquisition.yaml",
                "recipes/extract-units.yaml",
                "recipes/persistence-rules.yaml",
                "recipes/fact-intake.yaml",
                "recipes/freshness-rules.yaml",
                "recipes/exception-patterns.yaml",
                "recipes/answer-contract.yaml",
                "recipes/support-hierarchy.yaml",
                "recipes/confirmation-thresholds.yaml",
                "domain/operator-contract.yaml",
                "domain/coverage-ledger.yaml",
                "domain/OPERATIONS.md",
                "domain/ENRICHMENT_PROTOCOL.md",
                "templates/domain-pack/claims.json",
                "templates/domain-pack/answer.json",
                "templates/domain-pack/decision.json",
                "templates/domain-pack/expansion-plan.json",
            ):
                if entry not in required_reads:
                    failures.append({"path": "domain/operator-contract.yaml", "reason": f"required_reads missing entry: {entry}"})
            if currentness_enabled(profile):
                for entry in ("recipes/currentness-rules.yaml", "templates/domain-pack/currentness.json"):
                    if entry not in required_reads:
                        failures.append({"path": "domain/operator-contract.yaml", "reason": f"required_reads missing currentness entry: {entry}"})
        payload_templates = contract.get("payload_templates")
        if not isinstance(payload_templates, list) or not payload_templates:
            failures.append({"path": "domain/operator-contract.yaml", "reason": "payload_templates must be a non-empty list"})
        workflow = contract.get("workflow")
        if not isinstance(workflow, dict):
            failures.append({"path": "domain/operator-contract.yaml", "reason": "workflow must be an object"})
        else:
            for key in (
                "query_archive_first",
                "check_coverage_before_broad_claims",
                "use_enrichment_protocol_when_support_is_weak",
                "check_freshness_when_time_sensitive",
                "check_required_facts_before_case_application",
                "check_exception_patterns_before_base_rule_completion",
                "label_decisive_claims_with_support_hierarchy",
                "use_confirmation_thresholds_for_settled_conclusions",
                "follow_answer_contract_before_final_output",
                "auto_expand_when_below_target",
                "register_provisional_weak_slice_on_first_expand_gap",
                "resolve_provisional_weak_slice_after_enrichment",
            ):
                if workflow.get(key) is not True:
                    failures.append({"path": "domain/operator-contract.yaml", "reason": f"workflow.{key} must be true"})
            if currentness_enabled(profile):
                if workflow.get("build_currentness_bundle_before_decisive_current_answers") is not True:
                    failures.append({"path": "domain/operator-contract.yaml", "reason": "workflow.build_currentness_bundle_before_decisive_current_answers must be true"})
        commands = contract.get("commands")
        if not isinstance(commands, dict):
            failures.append({"path": "domain/operator-contract.yaml", "reason": "commands must be an object"})
        else:
            for key in (
                "coverage_state",
                "register_provisional_weak_slice",
                "resolve_provisional_weak_slice",
                "check_runner",
            ):
                value = commands.get(key)
                if not isinstance(value, str) or not value.strip():
                    failures.append({"path": "domain/operator-contract.yaml", "reason": f"commands.{key} must be a non-empty string"})
            if currentness_enabled(profile):
                for key in ("build_currentness_bundle", "check_currentness"):
                    value = commands.get(key)
                    if not isinstance(value, str) or not value.strip():
                        failures.append({"path": "domain/operator-contract.yaml", "reason": f"commands.{key} must be a non-empty string"})
        currentness_contract = contract.get("currentness")
        if not isinstance(currentness_contract, dict):
            failures.append({"path": "domain/operator-contract.yaml", "reason": "currentness must be an object"})
        elif bool(currentness_contract.get("enabled")) != currentness_enabled(profile):
            failures.append({"path": "domain/operator-contract.yaml", "reason": "currentness.enabled must match the domain profile"})

    freshness_rules_path = root / "recipes" / "freshness-rules.yaml"
    operations_path = root / "domain" / "OPERATIONS.md"
    if freshness_rules_path.exists() and operations_path.exists():
        freshness_rules = load_yaml(freshness_rules_path)
        refresh_required = str(bool(freshness_rules.get("refresh_before_answer"))).lower()
        operations_text = operations_path.read_text(encoding="utf-8")
        expected_line = f"- Refresh required before answer: `{refresh_required}`."
        if expected_line not in operations_text:
            failures.append(
                {
                    "path": "domain/OPERATIONS.md",
                    "reason": f"freshness posture drift: expected line `{expected_line}`",
                }
            )
    currentness_rules_path = root / "recipes" / "currentness-rules.yaml"
    if currentness_enabled(profile) and currentness_rules_path.exists():
        currentness_rules = load_yaml(currentness_rules_path)
        allowed_statuses = currentness_rules.get("allowed_statuses")
        if not isinstance(allowed_statuses, list) or not {"current", "stale", "superseded", "unproven"}.issubset(set(allowed_statuses)):
            failures.append(
                {
                    "path": "recipes/currentness-rules.yaml",
                    "reason": "allowed_statuses must include current, stale, superseded, and unproven",
                }
            )
        proof_fields = currentness_rules.get("proof_bundle_fields")
        if not isinstance(proof_fields, list) or not {"checked_at", "canonical_source_url"}.issubset(set(proof_fields)):
            failures.append(
                {
                    "path": "recipes/currentness-rules.yaml",
                    "reason": "proof_bundle_fields must include checked_at and canonical_source_url",
                }
            )
        if currentness_rules.get("block_decisive_current_answers_unless_status") != "current":
            failures.append(
                {
                    "path": "recipes/currentness-rules.yaml",
                    "reason": "block_decisive_current_answers_unless_status must be current",
                }
            )

    coverage_path = root / "domain" / "coverage-ledger.yaml"
    if coverage_path.exists():
        coverage = load_yaml(coverage_path)
        provisional = coverage.get("provisional_weak_slices")
        if not isinstance(provisional, list):
            failures.append(
                {
                    "path": "domain/coverage-ledger.yaml",
                    "reason": "provisional_weak_slices must be a list",
                }
            )
        support_gaps = coverage.get("support_gaps")
        if not isinstance(support_gaps, list):
            failures.append({"path": "domain/coverage-ledger.yaml", "reason": "support_gaps must be a list"})
        notes = coverage.get("notes")
        if not isinstance(notes, list):
            failures.append(
                {
                    "path": "domain/coverage-ledger.yaml",
                    "reason": "notes must be a list",
                }
            )
        else:
            if not any("Suggested provisional_weak_slices entry keys" in str(note) for note in notes):
                failures.append(
                    {
                        "path": "domain/coverage-ledger.yaml",
                        "reason": "missing provisional_weak_slices guidance note",
                    }
                )
            if not any("Suggested support_gaps entry keys" in str(note) for note in notes):
                failures.append(
                    {
                        "path": "domain/coverage-ledger.yaml",
                        "reason": "missing support_gaps guidance note",
                    }
                )
            if not any("Move a provisional weak slice to support_gaps" in str(note) for note in notes):
                failures.append(
                    {
                        "path": "domain/coverage-ledger.yaml",
                        "reason": "missing provisional weak-slice transition note",
                    }
                )
            if not any("Use provisional_weak_slices for likely below-target support" in str(note) for note in notes):
                failures.append(
                    {
                        "path": "domain/coverage-ledger.yaml",
                        "reason": "missing provisional weak-slice usage note",
                    }
                )

    protocol_path = root / "domain" / "ENRICHMENT_PROTOCOL.md"
    if protocol_path.exists():
        protocol_text = protocol_path.read_text(encoding="utf-8")
        for required_phrase in (
            "## Step 1: Classify the question",
            "## Step 2: Check local support",
            "## Step 3: Decide fetch vs ask-user",
            "## Step 4: Expansion path",
            "## Step 5: Reassess before answering",
            "## Stop conditions",
            "Run `check_coverage_state` when the question may sit on a partial topic or known support gap.",
            "If the answer is still provisional because of a known support gap, record `follow_up_action: expand`.",
            "Record the decision with `templates/domain-pack/decision.json`.",
        ):
            if required_phrase not in protocol_text:
                failures.append({"path": "domain/ENRICHMENT_PROTOCOL.md", "reason": f"missing protocol phrase: {required_phrase}"})

    answer_contract_path = root / "recipes" / "answer-contract.yaml"
    if answer_contract_path.exists():
        answer_contract = load_yaml(answer_contract_path)
        if answer_contract.get("auto_expand_when_below_target") is not True:
            failures.append(
                {
                    "path": "recipes/answer-contract.yaml",
                    "reason": "auto_expand_when_below_target must be true for generated packs",
                }
            )
        allowed = answer_contract.get("allow_non_expand_actions_when_below_target")
        if not isinstance(allowed, list) or "ask_user" not in allowed:
            failures.append(
                {
                    "path": "recipes/answer-contract.yaml",
                    "reason": "allow_non_expand_actions_when_below_target must include ask_user",
                }
            )

    playbooks_path = root / "recipes" / "source-playbooks.yaml"
    if playbooks_path.exists():
        playbooks_payload = load_yaml(playbooks_path)
        playbooks = playbooks_payload.get("playbooks")
        if not isinstance(playbooks, list) or not playbooks:
            failures.append({"path": "recipes/source-playbooks.yaml", "reason": "playbooks must be a non-empty list"})
        else:
            for index, playbook in enumerate(playbooks):
                if not isinstance(playbook, dict):
                    failures.append({"path": "recipes/source-playbooks.yaml", "reason": f"playbooks[{index}] must be an object"})
                    continue
                for key in (
                    "source_family",
                    "playbook_type",
                    "retrieval_unit",
                    "navigation_steps",
                    "persistence_expectation",
                    "exact_wording_default",
                    "discovery_strategy",
                    "supports_listing_sync",
                    "supports_direct_document_ingest",
                    "question_shape_search_guidance",
                ):
                    if key not in playbook:
                        failures.append(
                            {
                                "path": "recipes/source-playbooks.yaml",
                                "reason": f"playbooks[{index}] missing key: {key}",
                            }
                        )
    acquisition_path = root / "recipes" / "source-acquisition.yaml"
    if acquisition_path.exists():
        acquisition = load_yaml(acquisition_path)
        policies = acquisition.get("question_shape_policies")
        if not isinstance(policies, list) or not policies:
            failures.append({"path": "recipes/source-acquisition.yaml", "reason": "question_shape_policies must be a non-empty list"})
        else:
            for index, policy in enumerate(policies):
                if not isinstance(policy, dict):
                    failures.append({"path": "recipes/source-acquisition.yaml", "reason": f"question_shape_policies[{index}] must be an object"})
                    continue
                for key in ("name", "allowed_source_families", "preferred_source_family", "bounded_search"):
                    if key not in policy:
                        failures.append({"path": "recipes/source-acquisition.yaml", "reason": f"question_shape_policies[{index}] missing key: {key}"})
                bounded = policy.get("bounded_search")
                if isinstance(bounded, dict):
                    for key in (
                        "initial_query_budget",
                        "refinement_query_budget",
                        "allow_second_stage_refinement",
                        "allow_cross_family_fallback",
                    ):
                        if key not in bounded:
                            failures.append({"path": "recipes/source-acquisition.yaml", "reason": f"question_shape_policies[{index}].bounded_search missing key: {key}"})

    discovery_path = root / "recipes" / "source-discovery.yaml"
    if discovery_path.exists():
        discovery_payload = load_yaml(discovery_path)
        families = discovery_payload.get("families")
        if not isinstance(families, list) or not families:
            failures.append({"path": "recipes/source-discovery.yaml", "reason": "families must be a non-empty list"})
        else:
            for index, family in enumerate(families):
                if not isinstance(family, dict):
                    failures.append({"path": "recipes/source-discovery.yaml", "reason": f"families[{index}] must be an object"})
                    continue
                for key in (
                    "source_family",
                    "strategy",
                    "document_format",
                    "default_registry_state",
                    "ingest_steps",
                    "supports_temporary_ingest",
                    "freshness_state_path",
                    "transport_order",
                ):
                    if key not in family:
                        failures.append(
                            {
                                "path": "recipes/source-discovery.yaml",
                                "reason": f"families[{index}] missing key: {key}",
                            }
                        )
                transport_order = family.get("transport_order")
                if transport_order is not None and (
                    not isinstance(transport_order, list)
                    or not transport_order
                    or not all(isinstance(item, str) and item.strip() for item in transport_order)
                ):
                    failures.append(
                        {
                            "path": "recipes/source-discovery.yaml",
                            "reason": f"families[{index}].transport_order must be a non-empty list of strings",
                        }
                    )

    scenario_dir = root / "archive-evals" / "scenarios"
    scenario_count = 0
    if not scenario_dir.exists():
        failures.append({"path": "archive-evals/scenarios", "reason": "missing scenario directory"})
    else:
        for path in sorted(scenario_dir.glob("*.json")):
            scenario_count += 1
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                failures.append({"path": str(path.relative_to(root)), "reason": "invalid json"})
                continue
            for key in ("id", "bucket", "prompt", "expected_artifacts", "expected_constraints", "verifier_checks"):
                if key not in payload:
                    failures.append({"path": str(path.relative_to(root)), "reason": f"missing scenario key: {key}"})

    thresholds_path = root / "archive-evals" / "thresholds.json"
    if thresholds_path.exists():
        try:
            thresholds = json.loads(thresholds_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            failures.append({"path": "archive-evals/thresholds.json", "reason": "invalid json"})
            thresholds = {}
        for key in ("minimums", "maximums", "equals"):
            if key not in thresholds:
                failures.append({"path": "archive-evals/thresholds.json", "reason": f"missing threshold section: {key}"})

    return {
        "ok": not failures,
        "domain_slug": domain_slug,
        "scenario_count": scenario_count,
        "failures": failures,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive_root")
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    return emit(validate_pack(Path(args.archive_root).resolve()))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
