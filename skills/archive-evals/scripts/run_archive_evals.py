from __future__ import annotations

import argparse
import json
import math
import sqlite3
import subprocess
import sys
from collections import Counter, defaultdict
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
    query = title
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
        "query": query,
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
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if check_name == "check_claim_support":
        claims_path.unlink(missing_ok=True)
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


def retrieve_candidates(archive_root: Path, query: str, k: int) -> list[dict]:
    sqlite_path = archive_root / "index" / "navigation.sqlite"
    if sqlite_path.exists():
        try:
            return _retrieve_with_sqlite(sqlite_path, query, k)
        except sqlite3.DatabaseError:
            pass
    return _retrieve_with_fallback(load_documents(archive_root), query, k)


def _retrieve_with_sqlite(sqlite_path: Path, query: str, k: int) -> list[dict]:
    conn = sqlite3.connect(sqlite_path)
    try:
        rows = conn.execute(
            """
            select d.artifact_id, d.title, d.artifact_type, bm25(documents_fts) as score
            from documents_fts
            join documents d using (artifact_id)
            where documents_fts match ?
            order by score
            limit ?
            """,
            (query, k),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "artifact_id": artifact_id,
            "title": title,
            "artifact_type": artifact_type,
            "score": float(score),
        }
        for artifact_id, title, artifact_type, score in rows
    ]


def _retrieve_with_fallback(documents: list[dict], query: str, k: int) -> list[dict]:
    terms = [term for term in slugify(query).split("-") if term]
    scored = []
    for doc in documents:
        haystack = f"{doc.get('title', '')} {doc.get('search_text', '')}".lower()
        score = sum(haystack.count(term) for term in terms)
        if score > 0:
            scored.append(
                {
                    "artifact_id": doc["artifact_id"],
                    "title": doc.get("title", ""),
                    "artifact_type": doc.get("artifact_type", ""),
                    "score": float(score),
                }
            )
    scored.sort(key=lambda row: (-row["score"], row["artifact_id"]))
    return scored[:k]


def expected_relevance_map(scenario: dict) -> dict[str, float]:
    judgments = scenario.get("relevance_judgments")
    if isinstance(judgments, dict) and judgments:
        return {str(key): float(value) for key, value in judgments.items() if float(value) > 0}
    return {artifact_id: 1.0 for artifact_id in scenario.get("expected_artifacts", [])}


def compute_retrieval_metrics(retrieved_ids: list[str], relevance: dict[str, float], k: int) -> dict[str, float]:
    relevant_ids = {artifact_id for artifact_id, score in relevance.items() if score > 0}
    top_ids = retrieved_ids[:k]
    hits = [artifact_id for artifact_id in top_ids if artifact_id in relevant_ids]
    hit_at_k = 1.0 if hits else 0.0
    precision_at_k = len(hits) / k if k else 0.0
    recall_at_k = len(hits) / len(relevant_ids) if relevant_ids else 0.0

    mrr = 0.0
    for index, artifact_id in enumerate(top_ids, start=1):
        if artifact_id in relevant_ids:
            mrr = 1.0 / index
            break

    dcg = 0.0
    for index, artifact_id in enumerate(top_ids, start=1):
        rel = relevance.get(artifact_id, 0.0)
        if rel > 0:
            dcg += ((2**rel) - 1) / math.log2(index + 1)
    ideal_rels = sorted((score for score in relevance.values() if score > 0), reverse=True)[:k]
    idcg = 0.0
    for index, rel in enumerate(ideal_rels, start=1):
        idcg += ((2**rel) - 1) / math.log2(index + 1)
    ndcg = dcg / idcg if idcg else 0.0

    return {
        "hit_at_k": round(hit_at_k, 6),
        "precision_at_k": round(precision_at_k, 6),
        "recall_at_k": round(recall_at_k, 6),
        "mrr_at_k": round(mrr, 6),
        "ndcg_at_k": round(ndcg, 6),
    }


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

    query = scenario.get("query") or scenario["prompt"]
    k = int(scenario.get("retrieval_k", 5))
    retrieval_results = retrieve_candidates(archive_root, query, k)
    retrieved_ids = [row["artifact_id"] for row in retrieval_results]
    relevance = expected_relevance_map(scenario)
    retrieval_metrics = compute_retrieval_metrics(retrieved_ids, relevance, k)
    if scenario.get("expected_constraints", {}).get("require_any_artifact_match", False) and retrieval_metrics["hit_at_k"] == 0:
        failures.append({"reason": f"retrieval miss at k={k}"})

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
        "query": query,
        "retrieval_k": k,
        "expected_artifacts": expected_artifacts,
        "found_artifacts": found_artifacts,
        "retrieved_ids": retrieved_ids,
        "retrieval_results": retrieval_results,
        "retrieval_metrics": retrieval_metrics,
        "verifier_results": verifier_results,
        "failures": failures,
    }


def summarize_metrics(results: list[dict]) -> dict:
    metric_names = ("hit_at_k", "precision_at_k", "recall_at_k", "mrr_at_k", "ndcg_at_k")
    overall = {name: 0.0 for name in metric_names}
    bucket_totals: dict[str, dict[str, float]] = defaultdict(lambda: {name: 0.0 for name in metric_names})
    bucket_counts: Counter[str] = Counter()
    count = 0
    for result in results:
        metrics = result.get("retrieval_metrics", {})
        if not metrics:
            continue
        count += 1
        bucket_counts[result["bucket"]] += 1
        for name in metric_names:
            overall[name] += float(metrics.get(name, 0.0))
            bucket_totals[result["bucket"]][name] += float(metrics.get(name, 0.0))
    if count:
        overall = {name: round(value / count, 6) for name, value in overall.items()}
    by_bucket = {}
    for bucket, totals in bucket_totals.items():
        by_bucket[bucket] = {
            name: round(totals[name] / bucket_counts[bucket], 6)
            for name in metric_names
        }
    return {
        "scenario_count": count,
        "overall": overall,
        "by_bucket": by_bucket,
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
            "retrieval_metrics": summarize_metrics(results),
        },
    }
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
