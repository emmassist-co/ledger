from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


RECIPE_REFS = [
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
]


def run_json(cmd: list[str], cwd: Path | None = None) -> dict:
    completed = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "command failed")
    return json.loads(completed.stdout)


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def domain_pack_check_results(root: Path) -> list[dict]:
    checks: list[dict] = []
    profile_path = root / "recipes" / "domain-profile.yaml"
    profile = load_yaml(profile_path) if profile_path.exists() else {}

    def add(name: str, family: str, ok: bool, details: str) -> None:
        checks.append({"name": name, "family": family, "ok": ok, "details": details})

    add("domain_profile_present", "meta", profile_path.exists(), "recipes/domain-profile.yaml exists")

    source_families = root / "recipes" / "source-families.yaml"
    add("source_families_present", "source_families", source_families.exists(), "source family recipe exists")

    fact_intake_path = root / "recipes" / "fact-intake.yaml"
    fact_intake = load_yaml(fact_intake_path) if fact_intake_path.exists() else {}
    expected_case_policy = "block_if_missing" if profile.get("fact_sensitivity") == "required" else "warn_if_missing"
    add(
        "fact_intake_policy",
        "fact_intake",
        fact_intake.get("case_application_policy") == expected_case_policy,
        f"case_application_policy == {expected_case_policy}",
    )
    add(
        "fact_intake_required_facts",
        "fact_intake",
        bool(fact_intake.get("required_facts")),
        "required_facts are present in fact-intake recipe",
    )

    freshness_path = root / "recipes" / "freshness-rules.yaml"
    freshness = load_yaml(freshness_path) if freshness_path.exists() else {}
    expected_verified = bool(
        profile.get("volatility") in {"annual", "fast_changing"} or profile.get("risk_class") == "high"
    )
    add(
        "freshness_verified_at_policy",
        "freshness",
        freshness.get("require_verified_at_in_answers") == expected_verified,
        f"require_verified_at_in_answers == {expected_verified}",
    )

    exceptions_path = root / "recipes" / "exception-patterns.yaml"
    exceptions = load_yaml(exceptions_path) if exceptions_path.exists() else {}
    expected_exception_gate = profile.get("exception_density") in {"medium", "high"}
    add(
        "exception_policy",
        "exceptions",
        exceptions.get("require_exception_check_before_case_application") == expected_exception_gate,
        f"require_exception_check_before_case_application == {expected_exception_gate}",
    )
    add(
        "exception_classes_present",
        "exceptions",
        bool(exceptions.get("exception_classes")),
        "exception classes are present",
    )

    answer_contract_path = root / "recipes" / "answer-contract.yaml"
    answer_contract = load_yaml(answer_contract_path) if answer_contract_path.exists() else {}
    expected_sections = profile.get("answer_sections", [])
    add(
        "answer_contract_sections",
        "answer_contract",
        answer_contract.get("answer_sections") == expected_sections,
        "answer_sections match profile",
    )
    add(
        "answer_contract_flags",
        "answer_contract",
        bool(answer_contract.get("must_declare_output_mode"))
        and bool(answer_contract.get("must_declare_evidence_type")),
        "answer contract requires output mode and evidence type",
    )
    add(
        "exact_wording_contract",
        "exact_wording",
        answer_contract.get("exact_wording") == profile.get("exact_wording"),
        "answer contract exact_wording matches profile",
    )
    support_hierarchy_path = root / "recipes" / "support-hierarchy.yaml"
    support_hierarchy = load_yaml(support_hierarchy_path) if support_hierarchy_path.exists() else {}
    add(
        "support_hierarchy_present",
        "support_hierarchy",
        support_hierarchy_path.exists(),
        "support hierarchy recipe exists",
    )
    add(
        "support_hierarchy_policy",
        "support_hierarchy",
        support_hierarchy.get("decisive_claim_minimum") in {"extract", "raw_source", "derived_summary"},
        "support hierarchy defines a decisive claim minimum",
    )
    add(
        "support_hierarchy_requires_labels",
        "support_hierarchy",
        bool(support_hierarchy.get("require_support_label_per_decisive_claim")),
        "support hierarchy requires per-claim support labels",
    )
    confirmation_path = root / "recipes" / "confirmation-thresholds.yaml"
    confirmation = load_yaml(confirmation_path) if confirmation_path.exists() else {}
    add(
        "confirmation_thresholds_present",
        "confirmation_boundary",
        confirmation_path.exists(),
        "confirmation thresholds recipe exists",
    )
    add(
        "confirmation_levels_present",
        "confirmation_boundary",
        "confirmed_from_provided_facts" in set(confirmation.get("allowed_conclusion_levels", [])),
        "confirmation thresholds include a confirmed conclusion level",
    )
    add(
        "confirmation_blocking_facts_present",
        "confirmation_boundary",
        bool(confirmation.get("blocking_fact_ids")),
        "confirmation thresholds include blocking fact ids",
    )

    operator_path = root / "skills" / f"{profile.get('domain_slug', '')}-operator" / "SKILL.md"
    operator_text = operator_path.read_text(encoding="utf-8") if operator_path.exists() else ""
    add("operator_skill_present", "scope_boundary", operator_path.exists(), "domain operator skill exists")
    add(
        "operator_skill_references_recipes",
        "scope_boundary",
        all(ref in operator_text for ref in RECIPE_REFS),
        "operator skill references all generated recipes",
    )
    add(
        "operator_skill_modes",
        "scope_boundary",
        "rule_lookup" in operator_text and "case_application" in operator_text,
        "operator skill distinguishes rule_lookup and case_application",
    )
    add(
        "operator_skill_boundary_rule",
        "scope_boundary",
        "Do not turn a covered rule lookup into case application" in operator_text,
        "operator skill includes rule/case boundary rule",
    )
    add(
        "operator_skill_exact_wording",
        "exact_wording",
        f"Treat exact wording as `{profile.get('exact_wording')}` risk." in operator_text,
        "operator skill includes exact wording risk",
    )
    add(
        "operator_skill_support_rule",
        "support_hierarchy",
        "support hierarchy" in operator_text.lower(),
        "operator skill includes support hierarchy rule",
    )
    add(
        "operator_skill_confirmation_rule",
        "confirmation_boundary",
        "confirmation thresholds" in operator_text.lower(),
        "operator skill includes confirmation boundary rule",
    )
    add(
        "operator_skill_expansion_rule",
        "expansion",
        "validate it before fetching" in operator_text
        and "check_expansion_plan.py" in operator_text,
        "operator skill includes validated expansion workflow",
    )
    add(
        "coverage_ledger_present",
        "expansion",
        (root / "domain" / "coverage-ledger.yaml").exists(),
        "coverage ledger exists",
    )
    add(
        "expansion_report_template_present",
        "expansion",
        (root / "domain" / "expansion-report-template.md").exists(),
        "expansion report template exists",
    )
    acquisition_path = root / "recipes" / "source-acquisition.yaml"
    acquisition = load_yaml(acquisition_path) if acquisition_path.exists() else {}
    add(
        "source_acquisition_policy",
        "expansion",
        acquisition.get("acquisition_defaults", {}).get("official_source_capture_mode") == "on_use",
        "official source capture mode is on_use",
    )
    extract_units_path = root / "recipes" / "extract-units.yaml"
    extract_units = load_yaml(extract_units_path) if extract_units_path.exists() else {}
    add(
        "extract_units_present",
        "expansion",
        bool(extract_units.get("units")),
        "extract-units recipe includes at least one unit mapping",
    )
    persistence_path = root / "recipes" / "persistence-rules.yaml"
    persistence = load_yaml(persistence_path) if persistence_path.exists() else {}
    add(
        "persistence_rules_present",
        "expansion",
        bool(persistence.get("persist_when")) and bool(persistence.get("do_not_persist")),
        "persistence rules include keep and skip guidance",
    )

    thresholds_path = root / "archive-evals" / "thresholds.json"
    add("thresholds_present", "meta", thresholds_path.exists(), "archive-evals/thresholds.json exists")
    add(
        "domain_benchmark_thresholds_present",
        "meta",
        (root / "domain-benchmarks" / "thresholds.json").exists(),
        "domain-benchmarks/thresholds.json exists",
    )
    return checks


def summarize_checks(checks: list[dict]) -> dict:
    passed = sum(1 for check in checks if check["ok"])
    total = len(checks)
    by_family: dict[str, dict[str, float | int]] = {}
    grouped: dict[str, list[dict]] = {}
    for check in checks:
        grouped.setdefault(check["family"], []).append(check)
    for family, family_checks in grouped.items():
        family_passed = sum(1 for check in family_checks if check["ok"])
        by_family[family] = {
            "passed": family_passed,
            "total": len(family_checks),
            "pass_rate": round(family_passed / len(family_checks), 6) if family_checks else 0.0,
        }
    return {
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 6) if total else 0.0,
        "by_family": by_family,
        "checks": checks,
    }


def remove_generated_domain_pack(root: Path) -> None:
    shutil.rmtree(root / "domain", ignore_errors=True)
    shutil.rmtree(root / "domain-benchmarks", ignore_errors=True)
    skills_root = root / "skills"
    if skills_root.exists():
        for child in skills_root.iterdir():
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
    for relative in RECIPE_REFS[1:]:
        (root / relative).unlink(missing_ok=True)


def run_trial(repo_root: Path, example_root: Path) -> dict:
    eval_script = repo_root / "skills" / "archive-evals" / "scripts" / "run_archive_evals.py"
    scaffold_script = repo_root / "skills" / "domain-archive-pack-builder" / "scripts" / "scaffold_domain_pack.py"
    validate_script = repo_root / "skills" / "domain-archive-pack-builder" / "scripts" / "validate_domain_pack.py"

    with tempfile.TemporaryDirectory() as tmpdir:
        baseline_root = Path(tmpdir) / "baseline"
        packed_root = Path(tmpdir) / "packed"
        shutil.copytree(example_root, baseline_root)
        shutil.copytree(example_root, packed_root)

        remove_generated_domain_pack(baseline_root)
        baseline_eval = run_json([sys.executable, str(eval_script), "run", str(baseline_root)])
        baseline_pack = summarize_checks(domain_pack_check_results(baseline_root))

        profile_path = packed_root / "recipes" / "domain-profile.yaml"
        run_json(
            [sys.executable, str(scaffold_script), str(packed_root), "--profile", str(profile_path)],
            cwd=repo_root,
        )
        packed_validate = run_json([sys.executable, str(validate_script), str(packed_root)], cwd=repo_root)
        packed_eval = run_json([sys.executable, str(eval_script), "run", str(packed_root)])
        packed_pack = summarize_checks(domain_pack_check_results(packed_root))

        return {
            "baseline_eval": baseline_eval,
            "baseline_domain_pack": baseline_pack,
            "packed_validate": packed_validate,
            "packed_eval": packed_eval,
            "packed_domain_pack": packed_pack,
        }


def compare_family_scores(baseline: dict, packed: dict) -> dict:
    families = sorted(set(baseline["by_family"]) | set(packed["by_family"]))
    by_family = {}
    for family in families:
        base = float(baseline["by_family"].get(family, {}).get("pass_rate", 0.0))
        after = float(packed["by_family"].get(family, {}).get("pass_rate", 0.0))
        by_family[family] = {
            "baseline": round(base, 6),
            "with_domain_pack": round(after, 6),
            "delta": round(after - base, 6),
        }
    return by_family


def aggregate_family_scores(trial_results: list[dict]) -> dict:
    families = sorted(
        {
            family
            for trial in trial_results
            for family in set(trial["baseline_domain_pack"]["by_family"]) | set(trial["packed_domain_pack"]["by_family"])
        }
    )
    summary = {}
    for family in families:
        base_values = [float(trial["baseline_domain_pack"]["by_family"].get(family, {}).get("pass_rate", 0.0)) for trial in trial_results]
        packed_values = [float(trial["packed_domain_pack"]["by_family"].get(family, {}).get("pass_rate", 0.0)) for trial in trial_results]
        base_mean = sum(base_values) / len(base_values)
        packed_mean = sum(packed_values) / len(packed_values)
        summary[family] = {
            "baseline_mean": round(base_mean, 6),
            "with_domain_pack_mean": round(packed_mean, 6),
            "delta": round(packed_mean - base_mean, 6),
        }
    return summary


def evaluate_benchmark_thresholds(example_root: Path, payload: dict) -> dict:
    path = example_root / "domain-benchmarks" / "thresholds.json"
    if not path.exists():
        return {"checked": False, "ok": True, "failures": []}
    thresholds = load_json(path)
    failures = []
    family_scores = payload["family_scores"]
    for family, config in thresholds.get("families", {}).items():
        if not config.get("enabled", False):
            continue
        score = family_scores.get(family)
        if not score:
            failures.append({"family": family, "reason": "missing family score"})
            continue
        minimum_delta = float(config.get("minimum_delta", 0.0))
        if float(score["delta"]) < minimum_delta:
            failures.append({
                "family": family,
                "reason": "delta below minimum",
                "minimum_delta": minimum_delta,
                "actual_delta": score["delta"],
            })

    no_regression = thresholds.get("archive_no_regression", {})
    if no_regression.get("completion_pass_rate"):
        delta = float(payload["delta"]["archive_completion_pass_rate"])
        if delta < 0:
            failures.append({"family": "archive", "reason": "completion pass rate regressed", "actual_delta": delta})
    if no_regression.get("clean_pass_rate"):
        delta = float(payload["delta"]["archive_clean_pass_rate"])
        if delta < 0:
            failures.append({"family": "archive", "reason": "clean pass rate regressed", "actual_delta": delta})

    return {"checked": True, "ok": not failures, "failures": failures}


def benchmark(repo_root: Path, example_root: Path, trials: int) -> dict:
    trial_results = [run_trial(repo_root, example_root) for _ in range(trials)]

    baseline_rates = [trial["baseline_domain_pack"]["pass_rate"] for trial in trial_results]
    packed_rates = [trial["packed_domain_pack"]["pass_rate"] for trial in trial_results]
    baseline_clean = [
        trial["baseline_eval"]["trajectory_metrics"]["clean_pass_rate"] for trial in trial_results
    ]
    packed_clean = [
        trial["packed_eval"]["trajectory_metrics"]["clean_pass_rate"] for trial in trial_results
    ]
    baseline_completion = [
        trial["baseline_eval"]["trajectory_metrics"]["completion_pass_rate"] for trial in trial_results
    ]
    packed_completion = [
        trial["packed_eval"]["trajectory_metrics"]["completion_pass_rate"] for trial in trial_results
    ]
    payload = {
        "example": example_root.name,
        "trials": trials,
        "baseline": {
            "domain_pack_pass_rate_mean": round(sum(baseline_rates) / trials, 6),
            "archive_clean_pass_rate_mean": round(sum(baseline_clean) / trials, 6),
            "archive_completion_pass_rate_mean": round(sum(baseline_completion) / trials, 6),
        },
        "with_domain_pack": {
            "domain_pack_pass_rate_mean": round(sum(packed_rates) / trials, 6),
            "archive_clean_pass_rate_mean": round(sum(packed_clean) / trials, 6),
            "archive_completion_pass_rate_mean": round(sum(packed_completion) / trials, 6),
        },
        "delta": {
            "domain_pack_pass_rate": round((sum(packed_rates) - sum(baseline_rates)) / trials, 6),
            "archive_clean_pass_rate": round((sum(packed_clean) - sum(baseline_clean)) / trials, 6),
            "archive_completion_pass_rate": round((sum(packed_completion) - sum(baseline_completion)) / trials, 6),
        },
        "family_scores": aggregate_family_scores(trial_results),
        "last_trial": trial_results[-1],
    }
    payload["thresholds"] = evaluate_benchmark_thresholds(example_root, payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("example_root")
    parser.add_argument("--trials", type=int, default=3)
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    example_root = Path(args.example_root).resolve()
    repo_root = Path(__file__).resolve().parents[3]
    payload = benchmark(repo_root, example_root, args.trials)
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if payload["thresholds"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
