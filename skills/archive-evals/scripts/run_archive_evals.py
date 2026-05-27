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
from statistics import median


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


def get_by_path(payload: dict, path: str):
    current = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def load_thresholds(evals_root: Path) -> dict | None:
    path = evals_root / "thresholds.json"
    if not path.exists():
        return None
    return read_json(path)


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
    elif check_name == "check_exact_wording":
        claim = scenario.get("trajectory_expectations", {}).get("exact_wording_claim", {})
        claims_payload = {
            "claims": [
                {
                    "claim_id": claim.get("claim_id", f"{scenario['id']}-exact-1"),
                    "evidence_ids": claim.get("evidence_ids", scenario.get("expected_artifacts", [])),
                    "exact_wording": True,
                    "support_kind": claim.get("support_kind", "derived_summary"),
                }
            ]
        }
        claims_path = archive_root / "archive-evals" / "runs" / f"{scenario['id']}-exact-wording.json"
        write_json(claims_path, claims_payload)
        cmd += ["--claims-json", str(claims_path)]
    elif check_name == "check_decision_record":
        record = scenario.get("trajectory_expectations", {}).get("decision_record")
        if not isinstance(record, dict):
            return {
                "ok": False,
                "check": check_name,
                "summary": "decision record missing from scenario trajectory expectations",
                "failures": [{"reason": "missing trajectory_expectations.decision_record"}],
            }
        decision_path = archive_root / "archive-evals" / "runs" / f"{scenario['id']}-decision.json"
        write_json(decision_path, record)
        cmd += ["--decision-json", str(decision_path)]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if check_name in {"check_claim_support", "check_exact_wording"}:
        claims_path.unlink(missing_ok=True)
    if check_name == "check_decision_record":
        decision_path.unlink(missing_ok=True)
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


def build_trace_events(scenario: dict, retrieval_results: list[dict], verifier_results: list[dict]) -> list[str]:
    events = ["archive.query"]
    events.append("archive.retrieve.hit" if retrieval_results else "archive.retrieve.miss")
    policy_action = scenario.get("expected_constraints", {}).get("policy_action")
    if policy_action:
        events.append(f"policy_action.{policy_action}")
    decision = scenario.get("trajectory_expectations", {}).get("decision_record", {})
    action = decision.get("action")
    if action:
        events.append(f"decision.{action}")
    for result in verifier_results:
        check_name = result.get("check", "unknown")
        expected_ok = result.get("expected_ok", True)
        actual_ok = bool(result.get("ok"))
        if actual_ok:
            events.append(f"verifier.{check_name}.pass")
        elif not expected_ok:
            events.append(f"verifier.{check_name}.blocked")
        else:
            events.append(f"verifier.{check_name}.fail")
    return events


def first_relevant_rank(retrieved_ids: list[str], expected_artifacts: list[str]) -> int | None:
    expected = set(expected_artifacts)
    for index, artifact_id in enumerate(retrieved_ids, start=1):
        if artifact_id in expected:
            return index
    return None


def evaluate_trajectory(scenario: dict, retrieval_results: list[dict], verifier_results: list[dict]) -> dict:
    expectations = scenario.get("trajectory_expectations", {})
    retrieved_ids = [row["artifact_id"] for row in retrieval_results]
    events = build_trace_events(scenario, retrieval_results, verifier_results)
    drifts = []

    required_events = expectations.get("required_events", [])
    for event in required_events:
        if event not in events:
            drifts.append(f"missing required event: {event}")

    forbidden_events = expectations.get("forbidden_events", [])
    for event in forbidden_events:
        if event in events:
            drifts.append(f"forbidden event present: {event}")

    rank = first_relevant_rank(retrieved_ids, scenario.get("expected_artifacts", []))
    max_rank = expectations.get("max_first_relevant_rank")
    if isinstance(max_rank, int):
        if rank is None:
            drifts.append("no relevant artifact retrieved")
        elif rank > max_rank:
            drifts.append(f"first relevant artifact rank {rank} exceeds max {max_rank}")

    preferred_types = expectations.get("preferred_artifact_types", [])
    if preferred_types:
        preferred_types = set(preferred_types)
        matched = next(
            (
                row for row in retrieval_results
                if row["artifact_id"] in set(scenario.get("expected_artifacts", []))
            ),
            None,
        )
        if not matched:
            drifts.append("no relevant artifact available for preferred type check")
        elif matched.get("artifact_type") not in preferred_types:
            drifts.append(
                f"first relevant artifact type {matched.get('artifact_type')} not in preferred set"
            )

    max_verifier_calls = expectations.get("max_verifier_calls")
    if isinstance(max_verifier_calls, int) and len(verifier_results) > max_verifier_calls:
        drifts.append(
            f"verifier calls {len(verifier_results)} exceed max {max_verifier_calls}"
        )

    max_trace_steps = expectations.get("max_trace_steps")
    if isinstance(max_trace_steps, int) and len(events) > max_trace_steps:
        drifts.append(f"trace steps {len(events)} exceed max {max_trace_steps}")

    return {
        "events": events,
        "event_count": len(events),
        "verifier_count": len(verifier_results),
        "first_relevant_rank": rank,
        "drift_reasons": drifts,
    }


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

    expected_verifier_outcomes = scenario.get("expected_verifier_outcomes", {})
    for check_name in scenario.get("verifier_checks", []):
        result = run_verifier(archive_root, check_name, scenario)
        expected_ok = bool(expected_verifier_outcomes.get(check_name, True))
        result["expected_ok"] = expected_ok
        result["matched_expectation"] = bool(result.get("ok")) == expected_ok
        verifier_results.append(result)
        if not result["matched_expectation"]:
            failures.append({
                "reason": f"verifier outcome mismatch: {check_name}",
                "expected_ok": expected_ok,
                "actual_ok": bool(result.get("ok")),
                "details": result.get("failures", []),
            })
    trajectory = evaluate_trajectory(scenario, retrieval_results, verifier_results)
    if failures:
        status = "fail"
    elif trajectory["drift_reasons"]:
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
        "trajectory": trajectory,
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


def summarize_trajectory(results: list[dict]) -> dict:
    if not results:
        return {
            "scenario_count": 0,
            "completion_pass_rate": 0.0,
            "clean_pass_rate": 0.0,
            "drift_rate": 0.0,
            "median_trace_steps": 0,
            "median_verifier_calls": 0,
            "common_drift_modes": [],
        }

    completion_passes = 0
    clean_passes = 0
    drift_passes = 0
    trace_steps = []
    verifier_calls = []
    drift_reasons = Counter()
    for result in results:
        if result["status"] in {"pass", "pass_with_drift"}:
            completion_passes += 1
        if result["status"] == "pass":
            clean_passes += 1
        if result["status"] == "pass_with_drift":
            drift_passes += 1
        trajectory = result.get("trajectory", {})
        trace_steps.append(int(trajectory.get("event_count", 0)))
        verifier_calls.append(int(trajectory.get("verifier_count", 0)))
        for reason in trajectory.get("drift_reasons", []):
            drift_reasons[reason] += 1

    count = len(results)
    return {
        "scenario_count": count,
        "completion_pass_rate": round(completion_passes / count, 6),
        "clean_pass_rate": round(clean_passes / count, 6),
        "drift_rate": round(drift_passes / count, 6),
        "median_trace_steps": median(trace_steps),
        "median_verifier_calls": median(verifier_calls),
        "common_drift_modes": drift_reasons.most_common(5),
    }


def evaluate_thresholds(summary: dict, thresholds: dict | None) -> dict:
    if thresholds is None:
        return {
            "ok": True,
            "checked": False,
            "failures": [],
        }

    failures = []
    for path, minimum in thresholds.get("minimums", {}).items():
        try:
            actual = get_by_path(summary, path)
        except KeyError:
            failures.append({"path": path, "reason": "missing path for minimum check"})
            continue
        if float(actual) < float(minimum):
            failures.append({"path": path, "reason": "below minimum", "minimum": minimum, "actual": actual})

    for path, maximum in thresholds.get("maximums", {}).items():
        try:
            actual = get_by_path(summary, path)
        except KeyError:
            failures.append({"path": path, "reason": "missing path for maximum check"})
            continue
        if float(actual) > float(maximum):
            failures.append({"path": path, "reason": "above maximum", "maximum": maximum, "actual": actual})

    for path, expected in thresholds.get("equals", {}).items():
        try:
            actual = get_by_path(summary, path)
        except KeyError:
            failures.append({"path": path, "reason": "missing path for equals check"})
            continue
        if actual != expected:
            failures.append({"path": path, "reason": "not equal", "expected": expected, "actual": actual})

    return {
        "ok": not failures,
        "checked": True,
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
    summary = {
        "passes_by_bucket": dict(by_bucket),
        "totals_by_bucket": dict(total_by_bucket),
        "common_failure_modes": failure_reasons.most_common(5),
        "retrieval_metrics": summarize_metrics(results),
        "trajectory_metrics": summarize_trajectory(results),
    }
    summary["thresholds"] = evaluate_thresholds(summary, load_thresholds(evals_root))
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenario_count": len(results),
        "results": results,
        "summary": summary,
    }
    write_json(evals_root / "reports" / "latest.json", report)
    return report


def summarize_examples(examples_root: Path) -> dict:
    examples = []
    for example_root in sorted(path for path in examples_root.iterdir() if path.is_dir()):
        report_path = example_root / "archive-evals" / "reports" / "latest.json"
        if not report_path.exists():
            continue
        report = read_json(report_path)
        summary = report["summary"]
        examples.append({
            "example": example_root.name,
            "scenario_count": summary["retrieval_metrics"]["scenario_count"],
            "hit_at_k": summary["retrieval_metrics"]["overall"]["hit_at_k"],
            "mrr_at_k": summary["retrieval_metrics"]["overall"]["mrr_at_k"],
            "ndcg_at_k": summary["retrieval_metrics"]["overall"]["ndcg_at_k"],
            "completion_pass_rate": summary["trajectory_metrics"]["completion_pass_rate"],
            "clean_pass_rate": summary["trajectory_metrics"]["clean_pass_rate"],
            "drift_rate": summary["trajectory_metrics"]["drift_rate"],
            "thresholds_ok": summary.get("thresholds", {}).get("ok", True),
        })

    overall_ok = all(row["thresholds_ok"] for row in examples)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "examples": examples,
        "overall_ok": overall_ok,
    }
    write_json(examples_root / "benchmark-summary.json", payload)

    lines = [
        "# Benchmark Summary",
        "",
        "| Example | Scenarios | hit@k | mrr@k | ndcg@k | completion | clean | drift | thresholds |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in examples:
        lines.append(
            f"| `{row['example']}` | {row['scenario_count']} | {row['hit_at_k']:.6f} | {row['mrr_at_k']:.6f} | {row['ndcg_at_k']:.6f} | {row['completion_pass_rate']:.6f} | {row['clean_pass_rate']:.6f} | {row['drift_rate']:.6f} | {'pass' if row['thresholds_ok'] else 'fail'} |"
        )
    lines.extend([
        "",
        f"Overall thresholds: {'pass' if overall_ok else 'fail'}",
        "",
    ])
    (examples_root / "benchmark-summary.md").write_text("\n".join(lines), encoding="utf-8")
    return payload


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

    summarize = subparsers.add_parser("summarize-examples")
    summarize.add_argument("examples_root")

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    if args.command == "generate-corpus":
        archive_root = Path(args.archive_root).resolve()
        evals_root = ensure_workspace(archive_root)
        scenarios = generate_scenarios(archive_root, evals_root, args.limit)
        print(json.dumps({"ok": True, "generated": len(scenarios)}, ensure_ascii=True, indent=2))
        return 0
    if args.command == "run":
        archive_root = Path(args.archive_root).resolve()
        evals_root = ensure_workspace(archive_root)
        report = run_evals(archive_root, evals_root)
        print(json.dumps(report["summary"], ensure_ascii=True, indent=2))
        return 0 if report["summary"].get("thresholds", {}).get("ok", True) else 1
    if args.command == "summarize-examples":
        payload = summarize_examples(Path(args.examples_root).resolve())
        print(json.dumps(payload, ensure_ascii=True, indent=2))
        return 0 if payload["overall_ok"] else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
