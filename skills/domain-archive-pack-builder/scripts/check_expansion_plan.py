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
        "source_family",
        "source_url",
        "unit_type",
        "materialize_as",
        "persistence_action",
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

    allowed_families = {
        family["name"]
        for family in source_families.get("source_families", [])
        if isinstance(family, dict) and family.get("name")
    }
    source_family = plan.get("source_family")
    if source_family and source_family not in allowed_families:
        failures.append({"field": "source_family", "reason": f"not allowed: {source_family}"})

    if source_family:
        allowed_from_acquisition = set(acquisition.get("allowed_source_families", []))
        if source_family not in allowed_from_acquisition:
            failures.append({"field": "source_family", "reason": "not present in source-acquisition recipe"})

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

    return {
        "ok": not failures,
        "failures": failures,
        "checked": {
            "source_family": source_family,
            "task_type": task_type,
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
