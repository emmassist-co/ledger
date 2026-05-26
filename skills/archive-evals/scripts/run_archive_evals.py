from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def iter_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def slugify(text: str) -> str:
    out = []
    for ch in text.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in {" ", "-", "_"}:
            out.append("-")
    slug = "".join(out).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "scenario"


def load_documents(archive_root: Path) -> list[dict]:
    return iter_jsonl(archive_root / "index" / "documents.jsonl")


def choose_documents_for_bucket(documents: list[dict], bucket: str, limit: int) -> list[dict]:
    if bucket == "retrieval":
        preferred_types = ("resolution", "registry", "act", "block")
    elif bucket == "grounding":
        preferred_types = ("article_block", "block", "extract", "act")
    else:
        preferred_types = ("act", "resolution", "registry")
    preferred = []
    for artifact_type in preferred_types:
        preferred.extend([doc for doc in documents if doc.get("artifact_type") == artifact_type])
    seen = set()
    ordered = []
    for doc in preferred:
        artifact_id = doc.get("artifact_id")
        if artifact_id not in seen:
            seen.add(artifact_id)
            ordered.append(doc)
    return ordered[:limit]


def scenario_from_document(doc: dict, bucket: str) -> dict:
    artifact_id = doc["artifact_id"]
    title = doc.get("title") or artifact_id
    prompt = f"What does the archive know about {title}?"
    expected_constraints = {
        "require_any_artifact_match": True,
        "require_extract_evidence": bucket == "grounding",
        "policy_action": "answer",
        "coverage_term": title,
    }
    verifier_checks = ["check_coverage", "check_policy"]
    if bucket == "grounding":
        verifier_checks.append("check_claim_support")
    if bucket == "boundary":
        verifier_checks = ["check_policy", "check_provenance"]
    return {
        "id": f"{bucket}-{slugify(artifact_id)}",
        "bucket": bucket,
        "source_kind": "corpus_derived",
        "prompt": prompt,
        "expected_artifacts": [artifact_id],
        "expected_constraints": expected_constraints,
        "verifier_checks": verifier_checks,
    }


def generate_scenarios(archive_root: Path, evals_root: Path, limit: int) -> list[dict]:
    documents = load_documents(archive_root)
    buckets = ["retrieval", "grounding", "boundary"]
    scenarios = []
    per_bucket = max(1, limit // len(buckets))
    for bucket in buckets:
        for doc in choose_documents_for_bucket(documents, bucket, per_bucket):
            scenario = scenario_from_document(doc, bucket)
            scenarios.append(scenario)
            write_json(evals_root / "scenarios" / f"{scenario['id']}.json", scenario)
    return scenarios


def run_verifier(archive_root: Path, check_name: str, scenario: dict) -> dict:
    verifier = archive_root / "scripts" / "archive_verifier.py"
    if not verifier.exists():
        return {
            "ok": False,
            "check": check_name,
            "summary": "archive verifier missing",
            "failures": [{"reason": "missing scripts/archive_verifier.py"}],
        }
    cmd = [sys.executable, str(verifier), check_name, str(archive_root)]
    if check_name == "check_coverage":
        term = scenario.get("expected_constraints", {}).get("coverage_term", scenario["expected_artifacts"][0])
        cmd += ["--term", term]
    elif check_name == "check_policy":
        action = scenario.get("expected_constraints", {}).get("policy_action", "answer")
        autonomy = scenario.get("expected_constraints", {}).get("autonomy_policy", "proactive")
        cmd += ["--action", action, "--autonomy-policy", autonomy]
    elif check_name == "check_claim_support":
        claims_payload = {
            "claims": [
                {"claim_id": f"{scenario['id']}-claim-1", "evidence_ids": scenario["expected_artifacts"]}
            ]
        }
        claims_path = archive_root / "archive-evals" / "runs" / f"{scenario['id']}-claims.json"
        write_json(claims_path, claims_payload)
        cmd += ["--claims-json", str(claims_path)]
    completed = subprocess.run(cmd, capture_output=True, text=True)
    try:
        payload = json.loads(completed.stdout) if completed.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {
            "ok": False,
            "check": check_name,
            "summary": "verifier output was not valid JSON",
            "failures": [{"reason": completed.stdout.strip() or completed.stderr.strip() or "unknown"}],
        }
    return payload


def evaluate_scenario(archive_root: Path, documents: dict[str, dict], scenario: dict) -> dict:
    failures = []
    verifier_results = []
    expected_artifacts = scenario.get("expected_artifacts", [])
    found_artifacts = [artifact_id for artifact_id in expected_artifacts if artifact_id in documents]
    if scenario.get("expected_constraints", {}).get("require_any_artifact_match", False) and not found_artifacts:
        failures.append({"reason": "expected artifacts not present in archive index"})
    if scenario.get("expected_constraints", {}).get("require_extract_evidence", False):
        allowed = {"extract", "article_block", "block"}
        if not any(documents[a]["artifact_type"] in allowed for a in found_artifacts):
            failures.append({"reason": "no extract-like artifact present for grounding scenario"})
    for check_name in scenario.get("verifier_checks", []):
        result = run_verifier(archive_root, check_name, scenario)
        verifier_results.append(result)
        if not result.get("ok"):
            failures.append({"reason": f"verifier failed: {check_name}", "details": result.get("failures", [])})
    if failures:
        status = "fail"
    elif scenario["bucket"] == "boundary" and not verifier_results:
        status = "pass_with_drift"
    else:
        status = "pass"
    return {
        "id": scenario["id"],
        "bucket": scenario["bucket"],
        "status": status,
        "expected_artifacts": expected_artifacts,
        "found_artifacts": found_artifacts,
        "verifier_results": verifier_results,
        "failures": failures,
    }


def run_evals(archive_root: Path, evals_root: Path) -> dict:
    documents_list = load_documents(archive_root)
    documents = {doc["artifact_id"]: doc for doc in documents_list}
    scenario_paths = sorted((evals_root / "scenarios").glob("*.json"))
    results = [evaluate_scenario(archive_root, documents, read_json(path)) for path in scenario_paths]
    by_bucket = Counter(result["bucket"] for result in results if result["status"] == "pass")
    total_by_bucket = Counter(result["bucket"] for result in results)
    failure_reasons = Counter()
    for result in results:
        for failure in result["failures"]:
            failure_reasons[failure["reason"]] += 1
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenario_count": len(results),
        "results": results,
        "summary": {
            "passes_by_bucket": dict(by_bucket),
            "totals_by_bucket": dict(total_by_bucket),
            "common_failure_modes": failure_reasons.most_common(5),
        },
    }
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    write_json(evals_root / "reports" / f"report-{timestamp}.json", report)
    write_json(evals_root / "reports" / "latest.json", report)
    return report


def ensure_workspace(archive_root: Path) -> Path:
    evals_root = archive_root / "archive-evals"
    evals_root.mkdir(parents=True, exist_ok=True)
    for relative in ("scenarios", "reports", "runs"):
        (evals_root / relative).mkdir(parents=True, exist_ok=True)
    return evals_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen = subparsers.add_parser("generate-corpus")
    gen.add_argument("archive_root")
    gen.add_argument("--limit", type=int, default=6)

    run = subparsers.add_parser("run")
    run.add_argument("archive_root")

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    archive_root = Path(args.archive_root).resolve()
    evals_root = ensure_workspace(archive_root)
    if args.command == "generate-corpus":
        scenarios = generate_scenarios(archive_root, evals_root, args.limit)
        print(json.dumps({"ok": True, "generated": len(scenarios)}, ensure_ascii=True, indent=2))
        return 0
    if args.command == "run":
        report = run_evals(archive_root, evals_root)
        print(json.dumps(report["summary"], ensure_ascii=True, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
