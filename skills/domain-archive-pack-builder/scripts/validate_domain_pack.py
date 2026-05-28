from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from scaffold_domain_pack import validate_profile


REQUIRED_RECIPE_FILES = [
    "recipes/domain-profile.yaml",
    "recipes/source-families.yaml",
    "recipes/source-playbooks.yaml",
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

    operator_path = root / "skills" / f"{domain_slug}-operator" / "SKILL.md" if domain_slug else None
    if operator_path and not operator_path.exists():
        failures.append({"path": str(operator_path.relative_to(root)), "reason": "missing operator skill"})

    if operator_path and operator_path.exists():
        skill_text = operator_path.read_text(encoding="utf-8")
        for recipe_ref in (
            "recipes/source-families.yaml",
            "recipes/source-playbooks.yaml",
            "recipes/source-acquisition.yaml",
            "recipes/extract-units.yaml",
            "recipes/persistence-rules.yaml",
            "recipes/fact-intake.yaml",
            "recipes/freshness-rules.yaml",
            "recipes/exception-patterns.yaml",
            "recipes/answer-contract.yaml",
            "recipes/support-hierarchy.yaml",
            "recipes/confirmation-thresholds.yaml",
            "domain/coverage-ledger.yaml",
            "domain/OPERATIONS.md",
            "domain/ENRICHMENT_PROTOCOL.md",
        ):
            if recipe_ref not in skill_text:
                failures.append({"path": str(operator_path.relative_to(root)), "reason": f"missing recipe reference: {recipe_ref}"})
        for template_ref in (
            "templates/domain-pack/claims.json",
            "templates/domain-pack/answer.json",
            "templates/domain-pack/decision.json",
            "templates/domain-pack/expansion-plan.json",
        ):
            if template_ref not in skill_text:
                failures.append({"path": str(operator_path.relative_to(root)), "reason": f"missing helper template reference: {template_ref}"})
        for required_phrase in (
            "Query the archive first.",
            "Check the coverage ledger before claiming broad coverage or a negative result.",
            "Use `uv run python scripts/run_archive_check.py check_coverage_state ...` when a topic may be partial even if retrieval found something.",
            "Check required facts before case application.",
            "Check freshness before answering when the topic is time-sensitive.",
            "Check exception patterns before treating a base rule as complete.",
            "Use the support hierarchy to label decisive claims",
            "Use the confirmation thresholds before saying a person is confirmed",
            "Read `domain/ENRICHMENT_PROTOCOL.md` when local support is weak.",
        ):
            if required_phrase not in skill_text:
                failures.append(
                    {
                        "path": str(operator_path.relative_to(root)),
                        "reason": f"missing operator contract phrase: {required_phrase}",
                    }
                )

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

    coverage_path = root / "domain" / "coverage-ledger.yaml"
    if coverage_path.exists():
        coverage = load_yaml(coverage_path)
        support_gaps = coverage.get("support_gaps")
        if not isinstance(support_gaps, list):
            failures.append({"path": "domain/coverage-ledger.yaml", "reason": "support_gaps must be a list"})
        notes = coverage.get("notes")
        if not isinstance(notes, list) or not any("Suggested support_gaps entry keys" in str(note) for note in notes):
            failures.append(
                {
                    "path": "domain/coverage-ledger.yaml",
                    "reason": "missing support_gaps guidance note",
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
                ):
                    if key not in playbook:
                        failures.append(
                            {
                                "path": "recipes/source-playbooks.yaml",
                                "reason": f"playbooks[{index}] missing key: {key}",
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
