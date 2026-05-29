from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def emit(payload: dict) -> int:
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if payload.get("ok") else 1


def validate_plan(root: Path, plan: dict) -> dict:
    failures = []

    required = {
        "task_type",
        "question_shape",
        "source_family",
        "source_url",
        "unit_type",
        "materialize_as",
        "persistence_action",
        "search_stage",
        "query_terms",
        "reason",
    }
    missing = sorted(required - set(plan))
    for key in missing:
        failures.append({"field": key, "reason": "missing required field"})

    source_families = load_yaml(root / "recipes" / "source-families.yaml")
    acquisition = load_yaml(root / "recipes" / "source-acquisition.yaml")
    extract_units = load_yaml(root / "recipes" / "extract-units.yaml")
    persistence = load_yaml(root / "recipes" / "persistence-rules.yaml")
    answer_contract = load_yaml(root / "recipes" / "answer-contract.yaml")
    question_shape_policies = {
        row.get("name"): row
        for row in acquisition.get("question_shape_policies", [])
        if isinstance(row, dict) and row.get("name")
    }

    allowed_families = {
        family["name"]
        for family in source_families.get("source_families", [])
        if isinstance(family, dict) and family.get("name")
    }
    source_family = plan.get("source_family")
    question_shape = plan.get("question_shape")
    if source_family and source_family not in allowed_families:
        failures.append({"field": "source_family", "reason": f"not allowed: {source_family}"})
    if question_shape and question_shape not in question_shape_policies:
        failures.append({"field": "question_shape", "reason": f"unknown question shape: {question_shape}"})

    if source_family:
        allowed_from_acquisition = set(acquisition.get("allowed_source_families", []))
        if source_family not in allowed_from_acquisition:
            failures.append({"field": "source_family", "reason": "not present in source-acquisition recipe"})
    if question_shape and source_family and question_shape in question_shape_policies:
        allowed_for_shape = set(question_shape_policies[question_shape].get("allowed_source_families", []))
        if source_family not in allowed_for_shape:
            failures.append(
                {
                    "field": "source_family",
                    "reason": f"not allowed for question_shape {question_shape}: {source_family}",
                }
            )

    unit_map = {
        row.get("source_family"): row
        for row in extract_units.get("units", [])
        if isinstance(row, dict) and row.get("source_family")
    }
    unit_config = unit_map.get(source_family, {})
    if plan.get("unit_type") and unit_config:
        expected_unit = unit_config.get("retrieval_unit")
        if expected_unit and plan["unit_type"] != expected_unit:
            failures.append(
                {
                    "field": "unit_type",
                    "reason": f"expected {expected_unit} for source_family {source_family}",
                }
            )
        expected_materialized = unit_config.get("materialize_as")
        if expected_materialized and plan.get("materialize_as") != expected_materialized:
            failures.append(
                {
                    "field": "materialize_as",
                    "reason": f"expected {expected_materialized} for source_family {source_family}",
                }
            )

    if answer_contract.get("exact_wording") in {"important", "critical"} and plan.get("exact_wording_claim"):
        if plan.get("materialize_as") != "extract":
            failures.append(
                {
                    "field": "materialize_as",
                    "reason": "exact wording claims require extract materialization under this domain pack",
                }
            )

    task_type = plan.get("task_type")
    if task_type not in {"rule_lookup", "case_application"}:
        failures.append({"field": "task_type", "reason": "must be rule_lookup or case_application"})

    if task_type == "case_application" and not plan.get("facts_status"):
        failures.append({"field": "facts_status", "reason": "required for case_application"})

    allowed_persistence_actions = {"persist", "skip_persist"}
    if plan.get("persistence_action") not in allowed_persistence_actions:
        failures.append({"field": "persistence_action", "reason": "must be persist or skip_persist"})

    if plan.get("persistence_action") == "skip_persist":
        allowed_skip_reasons = set(acquisition.get("skip_persist_reasons", []))
        skip_reason = plan.get("skip_reason")
        if not skip_reason:
            failures.append({"field": "skip_reason", "reason": "required when persistence_action is skip_persist"})
        elif skip_reason not in allowed_skip_reasons:
            failures.append({"field": "skip_reason", "reason": f"not allowed: {skip_reason}"})

    if plan.get("persistence_action") == "persist":
        if plan.get("materialize_as") == "temporary_case_note":
            failures.append({"field": "materialize_as", "reason": "temporary_case_note should not be persisted"})

    if not str(plan.get("source_url", "")).strip():
        failures.append({"field": "source_url", "reason": "must be non-empty"})

    search_stage = plan.get("search_stage")
    if search_stage not in {"initial", "refinement"}:
        failures.append({"field": "search_stage", "reason": "must be initial or refinement"})
    query_terms = plan.get("query_terms")
    if not isinstance(query_terms, list) or not query_terms or not all(isinstance(term, str) and term.strip() for term in query_terms):
        failures.append({"field": "query_terms", "reason": "must be a non-empty list of strings"})
    if question_shape in question_shape_policies and isinstance(query_terms, list):
        bounded_search = question_shape_policies[question_shape].get("bounded_search", {})
        initial_budget = bounded_search.get("initial_query_budget")
        refinement_budget = bounded_search.get("refinement_query_budget")
        if search_stage == "initial" and isinstance(initial_budget, int) and len(query_terms) > initial_budget:
            failures.append(
                {
                    "field": "query_terms",
                    "reason": f"initial search exceeds budget for question_shape {question_shape}",
                }
            )
        if search_stage == "refinement":
            if bounded_search.get("allow_second_stage_refinement") is not True:
                failures.append(
                    {
                        "field": "search_stage",
                        "reason": f"refinement not allowed for question_shape {question_shape}",
                    }
                )
            if isinstance(refinement_budget, int) and len(query_terms) > refinement_budget:
                failures.append(
                    {
                        "field": "query_terms",
                        "reason": f"refinement search exceeds budget for question_shape {question_shape}",
                    }
                )

    return {
        "ok": not failures,
        "failures": failures,
        "checked": {
            "source_family": source_family,
            "question_shape": question_shape,
            "task_type": task_type,
            "search_stage": search_stage,
            "materialize_as": plan.get("materialize_as"),
            "persistence_action": plan.get("persistence_action"),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive_root")
    parser.add_argument("--plan-json", required=True)
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    root = Path(args.archive_root).resolve()
    plan = load_json(Path(args.plan_json).resolve())
    return emit(validate_plan(root, plan))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
