from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


REQUIRED_RECIPE_FILES = [
    "recipes/domain-profile.yaml",
    "recipes/source-families.yaml",
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
    "domain/coverage-ledger.yaml",
    "domain/expansion-report-template.md",
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

    operator_path = root / "skills" / f"{domain_slug}-operator" / "SKILL.md" if domain_slug else None
    if operator_path and not operator_path.exists():
        failures.append({"path": str(operator_path.relative_to(root)), "reason": "missing operator skill"})

    if operator_path and operator_path.exists():
        skill_text = operator_path.read_text(encoding="utf-8")
        for recipe_ref in (
            "recipes/source-families.yaml",
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
        ):
            if recipe_ref not in skill_text:
                failures.append({"path": str(operator_path.relative_to(root)), "reason": f"missing recipe reference: {recipe_ref}"})

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
