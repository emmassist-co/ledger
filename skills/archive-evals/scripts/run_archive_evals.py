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

import yaml


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


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


def parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def infer_case_metadata(scenario: dict) -> dict:
    metadata = scenario.get("case_metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    origin = metadata.get("origin") or scenario.get("source_kind") or "unspecified"
    tier = metadata.get("tier")
    if tier is None:
        if origin == "user_seeded":
            tier = "golden"
        elif origin == "production_derived":
            tier = "regression"
        else:
            tier = "coverage"
    critical_path = metadata.get("critical_path")
    if critical_path is None:
        critical_path = tier == "golden"
    criticality = metadata.get("criticality")
    if criticality is None:
        criticality = "high" if critical_path else "medium"
    return {
        "tier": tier,
        "criticality": criticality,
        "critical_path": bool(critical_path),
        "origin": origin,
        "failure_class": metadata.get("failure_class"),
        "source_trace_id": metadata.get("source_trace_id"),
        "stale_after_days": metadata.get("stale_after_days"),
        "added_at": metadata.get("added_at"),
        "last_failed_at": metadata.get("last_failed_at"),
        "last_reviewed_at": metadata.get("last_reviewed_at"),
        "last_meaningful_update_at": metadata.get("last_meaningful_update_at"),
    }


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
        "case_metadata": {
            "tier": "coverage",
            "criticality": "medium",
            "critical_path": False,
            "origin": "corpus_derived",
            "stale_after_days": 90,
        },
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
    helper = archive_root / "scripts" / "run_archive_check.py"
    if not verifier.exists():
        return {
            "ok": False,
            "check": check_name,
            "summary": "archive verifier missing",
            "failures": [{"reason": "missing scripts/archive_verifier.py"}],
        }
    use_helper = check_name in {"check_coverage_state", "check_auto_expand_decision"}
    runner = helper if use_helper and helper.exists() else verifier
    if use_helper and not helper.exists():
        return {
            "ok": False,
            "check": check_name,
            "summary": "archive helper missing",
            "failures": [{"reason": "missing scripts/run_archive_check.py"}],
        }
    cmd = [sys.executable, str(runner)]
    if use_helper:
        cmd += [check_name, "--archive-root", str(archive_root)]
    else:
        cmd += [check_name, str(archive_root)]
    if check_name == "check_coverage":
        term = scenario.get("expected_constraints", {}).get("coverage_term", scenario["expected_artifacts"][0])
        cmd += ["--term", term]
    elif check_name == "check_coverage_state":
        term = scenario.get("expected_constraints", {}).get("coverage_term", scenario["expected_artifacts"][0])
        task_type = scenario.get("expected_constraints", {}).get("task_type", "rule_lookup")
        cmd += ["--term", term, "--task-type", task_type]
    elif check_name == "check_auto_expand_decision":
        record = scenario.get("trajectory_expectations", {}).get("decision_record")
        if not isinstance(record, dict):
            return {
                "ok": False,
                "check": check_name,
                "summary": "decision record missing from scenario trajectory expectations",
                "failures": [{"reason": "missing trajectory_expectations.decision_record"}],
            }
        term = scenario.get("expected_constraints", {}).get("coverage_term", scenario["expected_artifacts"][0])
        task_type = scenario.get("expected_constraints", {}).get("task_type", "rule_lookup")
        decision_path = archive_root / "archive-evals" / "runs" / f"{scenario['id']}-auto-expand-decision.json"
        write_json(decision_path, record)
        cmd += ["--term", term, "--task-type", task_type, "--decision-json", str(decision_path)]
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
    if check_name == "check_auto_expand_decision":
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


def infer_response_mode(scenario: dict, verifier_results: list[dict]) -> str:
    if any((not result.get("expected_ok", True)) and result.get("matched_expectation") for result in verifier_results):
        decision = scenario.get("trajectory_expectations", {}).get("decision_record", {})
        if str(decision.get("action", "")).lower() == "expand":
            return "expand_then_answer"
        return "safety_block"
    decision = scenario.get("trajectory_expectations", {}).get("decision_record", {})
    action = str(decision.get("action", "")).lower()
    reason = str(decision.get("reason", "")).lower()
    if action == "expand":
        return "expand_then_answer"
    if action == "ask_user" or "pending facts" in reason or "missing facts" in reason:
        return "answer_with_missing_facts"
    return "direct_answer"


def evaluate_answer_expectations(archive_root: Path, scenario: dict, verifier_results: list[dict]) -> dict:
    expectations = scenario.get("answer_expectations")
    if not isinstance(expectations, dict):
        return {
            "checked": False,
            "ok": True,
            "actual_response_mode": infer_response_mode(scenario, verifier_results),
            "failures": [],
        }

    answer_contract_path = archive_root / "recipes" / "answer-contract.yaml"
    answer_contract = read_yaml(answer_contract_path) if answer_contract_path.exists() else {}
    failures = []

    expected_action = expectations.get("expected_decision_action")
    if expected_action is not None:
        actual_action = scenario.get("trajectory_expectations", {}).get("decision_record", {}).get("action")
        if actual_action != expected_action:
            failures.append(
                {
                    "field": "expected_decision_action",
                    "reason": "decision action mismatch",
                    "expected": expected_action,
                    "actual": actual_action,
                }
            )

    expected_quality_status = expectations.get("minimum_quality_status")
    if expected_quality_status is not None:
        decision = scenario.get("trajectory_expectations", {}).get("decision_record", {})
        actual_quality_status = decision.get("quality_status")
        if actual_quality_status != expected_quality_status:
            failures.append(
                {
                    "field": "minimum_quality_status",
                    "reason": "quality status mismatch",
                    "expected": expected_quality_status,
                    "actual": actual_quality_status,
                }
            )

    required_sections = expectations.get("required_answer_sections", [])
    if required_sections:
        actual_sections = set(answer_contract.get("answer_sections", []))
        missing_sections = [section for section in required_sections if section not in actual_sections]
        if missing_sections:
            failures.append(
                {
                    "field": "required_answer_sections",
                    "reason": "answer contract missing required sections",
                    "missing": missing_sections,
                }
            )

    for field_name in ("must_declare_missing_facts", "must_declare_verified_at"):
        if field_name in expectations:
            expected_value = bool(expectations[field_name])
            actual_value = bool(answer_contract.get(field_name))
            if actual_value != expected_value:
                failures.append(
                    {
                        "field": field_name,
                        "reason": "answer contract flag mismatch",
                        "expected": expected_value,
                        "actual": actual_value,
                    }
                )

    expected_mode = expectations.get("response_mode")
    actual_mode = infer_response_mode(scenario, verifier_results)
    if expected_mode and actual_mode != expected_mode:
        failures.append(
            {
                "field": "response_mode",
                "reason": "response mode mismatch",
                "expected": expected_mode,
                "actual": actual_mode,
            }
        )

    replay_expected_mode = expectations.get("replay_expected_response_mode")
    replay_check = None
    if replay_expected_mode:
        replay_check = {
            "checked": True,
            "ok": actual_mode == replay_expected_mode,
            "expected": replay_expected_mode,
            "actual": actual_mode,
        }
        if not replay_check["ok"]:
            failures.append(
                {
                    "field": "replay_expected_response_mode",
                    "reason": "replay response mode mismatch",
                    "expected": replay_expected_mode,
                    "actual": actual_mode,
                }
            )

    false_completion_expected_mode = expectations.get("false_completion_expected_response_mode")
    false_completion_check = None
    if false_completion_expected_mode:
        false_completion_check = {
            "checked": True,
            "ok": actual_mode == false_completion_expected_mode,
            "expected": false_completion_expected_mode,
            "actual": actual_mode,
        }
        if not false_completion_check["ok"]:
            failures.append(
                {
                    "field": "false_completion_expected_response_mode",
                    "reason": "false completion guard mismatch",
                    "expected": false_completion_expected_mode,
                    "actual": actual_mode,
                }
            )

    return {
        "checked": True,
        "ok": not failures,
        "actual_response_mode": actual_mode,
        "replay_check": replay_check,
        "false_completion_check": false_completion_check,
        "failures": failures,
    }


def evaluate_source_policy(scenario: dict, retrieval_results: list[dict]) -> dict:
    expectations = scenario.get("answer_expectations")
    if not isinstance(expectations, dict):
        return {"checked": False, "ok": True, "failures": []}

    allowed = expectations.get("allowed_source_systems")
    if not isinstance(allowed, list) or not allowed:
        return {"checked": False, "ok": True, "failures": []}

    allowed_set = {str(item) for item in allowed if str(item).strip()}
    retrieved_systems = [
        str(row.get("source_system"))
        for row in retrieval_results
        if isinstance(row.get("source_system"), str) and row.get("source_system").strip()
    ]
    top_source_system = retrieved_systems[0] if retrieved_systems else None
    ok = top_source_system in allowed_set if top_source_system else False
    failures = []
    if top_source_system and not ok:
        failures.append(
            {
                "reason": "top retrieved source outside allowed source systems",
                "allowed_source_systems": sorted(allowed_set),
                "actual_source_system": top_source_system,
            }
        )
    return {
        "checked": bool(retrieved_systems),
        "ok": ok,
        "allowed_source_systems": sorted(allowed_set),
        "top_source_system": top_source_system,
        "retrieved_source_systems": retrieved_systems,
        "failures": failures,
    }


def evaluate_query_efficiency(archive_root: Path, scenario: dict) -> dict:
    decision = scenario.get("trajectory_expectations", {}).get("decision_record", {})
    question_shape = decision.get("question_shape")
    search_stage = decision.get("search_stage")
    query_terms = decision.get("query_terms")
    if not isinstance(question_shape, str) or not isinstance(search_stage, str) or not isinstance(query_terms, list):
        return {"checked": False, "ok": True, "failures": []}

    acquisition_path = archive_root / "recipes" / "source-acquisition.yaml"
    acquisition = read_yaml(acquisition_path) if acquisition_path.exists() else {}
    policies = acquisition.get("question_shape_policies", {})
    if not isinstance(policies, dict):
        return {"checked": False, "ok": True, "failures": []}
    policy = policies.get(question_shape)
    if not isinstance(policy, dict):
        return {"checked": False, "ok": True, "failures": []}

    bounded = policy.get("bounded_search", {})
    failures = []
    if search_stage == "initial":
        budget = bounded.get("initial_query_budget")
        if isinstance(budget, int) and len(query_terms) > budget:
            failures.append(
                {
                    "reason": "initial query budget exceeded",
                    "question_shape": question_shape,
                    "budget": budget,
                    "actual": len(query_terms),
                }
            )
    elif search_stage == "refinement":
        if not bounded.get("allow_second_stage_refinement", False):
            failures.append(
                {
                    "reason": "refinement used when question shape disallows it",
                    "question_shape": question_shape,
                }
            )
        budget = bounded.get("refinement_query_budget")
        if isinstance(budget, int) and len(query_terms) > budget:
            failures.append(
                {
                    "reason": "refinement query budget exceeded",
                    "question_shape": question_shape,
                    "budget": budget,
                    "actual": len(query_terms),
                }
            )

    return {
        "checked": True,
        "ok": not failures,
        "question_shape": question_shape,
        "search_stage": search_stage,
        "query_terms": query_terms,
        "query_count": len(query_terms),
        "failures": failures,
    }


def evaluate_expand_mode(archive_root: Path, scenario: dict, retrieval_results: list[dict], answer_evaluation: dict) -> dict:
    expectations = scenario.get("answer_expectations")
    if not isinstance(expectations, dict) or expectations.get("run_mode") != "expand_mode_primary":
        return {"checked": False, "ok": True, "failures": []}

    decision = scenario.get("trajectory_expectations", {}).get("decision_record", {})
    actual_mode = answer_evaluation.get("actual_response_mode", "unknown")
    source_policy = evaluate_source_policy(scenario, retrieval_results)
    query_efficiency = evaluate_query_efficiency(archive_root, scenario)
    failures = []

    if source_policy.get("checked") and not source_policy.get("ok"):
        failures.extend(source_policy.get("failures", []))
    if query_efficiency.get("checked") and not query_efficiency.get("ok"):
        failures.extend(query_efficiency.get("failures", []))

    return {
        "checked": True,
        "ok": not failures,
        "actual_response_mode": actual_mode,
        "decision_action": decision.get("action"),
        "persistence_action": decision.get("persistence_action"),
        "source_policy": source_policy,
        "query_efficiency": query_efficiency,
        "failures": failures,
    }


def scenario_passed(result: dict) -> bool:
    return result["status"] in {"pass", "pass_with_drift"}


def scenario_clean_passed(result: dict) -> bool:
    return result["status"] == "pass"


def select_reference_timestamp(metadata: dict) -> tuple[str | None, datetime | None, str | None]:
    for field in (
        "last_failed_at",
        "last_meaningful_update_at",
        "last_reviewed_at",
        "added_at",
    ):
        parsed = parse_datetime(metadata.get(field))
        if parsed is not None:
            return field, parsed, metadata.get(field)
    return None, None, None


def evaluate_scenario(archive_root: Path, documents: dict[str, dict], scenario: dict) -> dict:
    failures = []
    verifier_results = []
    case_metadata = infer_case_metadata(scenario)
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
    for row in retrieval_results:
        doc = documents.get(row["artifact_id"], {})
        row["source_system"] = doc.get("source_system")
        row["source_url"] = doc.get("source_url")
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
    answer_evaluation = evaluate_answer_expectations(archive_root, scenario, verifier_results)
    expand_mode_evaluation = evaluate_expand_mode(
        archive_root, scenario, retrieval_results, answer_evaluation
    )
    if answer_evaluation["checked"] and not answer_evaluation["ok"]:
        failures.extend(
            {"reason": f"answer expectation mismatch: {failure['field']}", "details": failure}
            for failure in answer_evaluation["failures"]
        )
    if expand_mode_evaluation["checked"] and not expand_mode_evaluation["ok"]:
        failures.extend(
            {"reason": f"expand mode policy mismatch: {failure['reason']}", "details": failure}
            for failure in expand_mode_evaluation["failures"]
        )
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
        "case_metadata": case_metadata,
        "query": query,
        "retrieval_k": k,
        "expected_artifacts": expected_artifacts,
        "found_artifacts": found_artifacts,
        "retrieved_ids": retrieved_ids,
        "retrieval_results": retrieval_results,
        "retrieval_metrics": retrieval_metrics,
        "verifier_results": verifier_results,
        "trajectory": trajectory,
        "answer_evaluation": answer_evaluation,
        "expand_mode_evaluation": expand_mode_evaluation,
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


def summarize_answer_quality(results: list[dict]) -> dict:
    checked = [result for result in results if result.get("answer_evaluation", {}).get("checked")]
    if not checked:
        return {
            "scenario_count": 0,
            "pass_rate": 0.0,
            "response_modes": {},
            "common_failures": [],
        }

    passes = 0
    response_modes = Counter()
    failures = Counter()
    for result in checked:
        evaluation = result.get("answer_evaluation", {})
        if evaluation.get("ok"):
            passes += 1
        response_modes[evaluation.get("actual_response_mode", "unknown")] += 1
        for failure in evaluation.get("failures", []):
            failures[failure.get("reason", "unknown")] += 1

    count = len(checked)
    return {
        "scenario_count": count,
        "pass_rate": round(passes / count, 6),
        "response_modes": dict(response_modes),
        "common_failures": failures.most_common(5),
    }


def summarize_replay_metrics(results: list[dict]) -> dict:
    checked = []
    failures = Counter()
    for result in results:
        replay_check = result.get("answer_evaluation", {}).get("replay_check")
        if isinstance(replay_check, dict) and replay_check.get("checked"):
            checked.append(replay_check)
            if not replay_check.get("ok"):
                failures["replay response mode mismatch"] += 1

    if not checked:
        return {
            "scenario_count": 0,
            "second_run_local_hit_rate": None,
            "common_failures": [],
        }

    passes = sum(1 for item in checked if item.get("ok"))
    return {
        "scenario_count": len(checked),
        "second_run_local_hit_rate": round(passes / len(checked), 6),
        "common_failures": failures.most_common(5),
    }


def summarize_false_completion_metrics(results: list[dict]) -> dict:
    checked = []
    failures = Counter()
    for result in results:
        guard_check = result.get("answer_evaluation", {}).get("false_completion_check")
        if isinstance(guard_check, dict) and guard_check.get("checked"):
            checked.append(guard_check)
            if not guard_check.get("ok"):
                failures["false completion guard mismatch"] += 1

    if not checked:
        return {
            "scenario_count": 0,
            "guard_success_rate": None,
            "false_completion_rate": None,
            "common_failures": [],
        }

    passes = sum(1 for item in checked if item.get("ok"))
    count = len(checked)
    guard_success_rate = round(passes / count, 6)
    return {
        "scenario_count": count,
        "guard_success_rate": guard_success_rate,
        "false_completion_rate": round(1.0 - guard_success_rate, 6),
        "common_failures": failures.most_common(5),
    }


def summarize_expand_mode_metrics(results: list[dict]) -> dict:
    checked = [
        result
        for result in results
        if isinstance(result.get("expand_mode_evaluation"), dict)
        and result["expand_mode_evaluation"].get("checked")
    ]
    if not checked:
        return {
            "scenario_count": 0,
            "expand_success_rate": None,
            "answer_pass_rate_after_expand": None,
            "persistence_success_rate": None,
            "wrong_source_rate": None,
            "query_efficiency_failure_rate": None,
            "bounded_failure_rate": None,
            "common_failures": [],
        }

    expand_successes = 0
    answer_passes = 0
    persistence_successes = 0
    wrong_sources = 0
    query_failures = 0
    bounded_failures = 0
    failures = Counter()

    for result in checked:
        evaluation = result["expand_mode_evaluation"]
        source_policy = evaluation.get("source_policy", {})
        query_efficiency = evaluation.get("query_efficiency", {})
        if evaluation.get("ok") and scenario_passed(result):
            expand_successes += 1
        if result.get("answer_evaluation", {}).get("ok") and evaluation.get("actual_response_mode") == "expand_then_answer":
            answer_passes += 1
        if (
            evaluation.get("actual_response_mode") == "expand_then_answer"
            and evaluation.get("persistence_action") == "persist"
            and scenario_passed(result)
        ):
            persistence_successes += 1
        if source_policy.get("checked") and not source_policy.get("ok"):
            wrong_sources += 1
            for failure in source_policy.get("failures", []):
                failures[failure.get("reason", "unknown")] += 1
        if query_efficiency.get("checked") and not query_efficiency.get("ok"):
            query_failures += 1
            for failure in query_efficiency.get("failures", []):
                failures[failure.get("reason", "unknown")] += 1
        if (
            not scenario_passed(result)
            and not (source_policy.get("checked") and not source_policy.get("ok"))
            and not (query_efficiency.get("checked") and not query_efficiency.get("ok"))
            and evaluation.get("actual_response_mode") == "safety_block"
        ):
            bounded_failures += 1
        for failure in evaluation.get("failures", []):
            failures[failure.get("reason", "unknown")] += 1

    count = len(checked)
    expanded = [
        result
        for result in checked
        if result["expand_mode_evaluation"].get("actual_response_mode") == "expand_then_answer"
    ]
    expanded_count = len(expanded)
    return {
        "scenario_count": count,
        "expand_success_rate": round(expand_successes / count, 6),
        "answer_pass_rate_after_expand": round(answer_passes / expanded_count, 6) if expanded_count else None,
        "persistence_success_rate": round(persistence_successes / expanded_count, 6) if expanded_count else None,
        "wrong_source_rate": round(wrong_sources / count, 6),
        "query_efficiency_failure_rate": round(query_failures / count, 6),
        "bounded_failure_rate": round(bounded_failures / count, 6),
        "common_failures": failures.most_common(5),
    }


def summarize_suite_health(results: list[dict]) -> dict:
    tiers = Counter()
    origins = Counter()
    criticalities = Counter()
    golden = []
    critical_path = []
    failing_priority_cases = []

    priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    for result in results:
        metadata = result.get("case_metadata", {})
        tier = str(metadata.get("tier", "coverage"))
        origin = str(metadata.get("origin", "unspecified"))
        criticality = str(metadata.get("criticality", "medium"))
        tiers[tier] += 1
        origins[origin] += 1
        criticalities[criticality] += 1
        if tier == "golden":
            golden.append(result)
        if metadata.get("critical_path"):
            critical_path.append(result)
        if (tier == "golden" or metadata.get("critical_path")) and not scenario_passed(result):
            failing_priority_cases.append(result)

    failing_priority_cases.sort(
        key=lambda item: (
            priority_rank.get(item.get("case_metadata", {}).get("criticality", "medium"), 9),
            item["id"],
        )
    )

    def pass_rate(items: list[dict]) -> float | None:
        if not items:
            return None
        return round(sum(1 for item in items if scenario_passed(item)) / len(items), 6)

    def clean_rate(items: list[dict]) -> float | None:
        if not items:
            return None
        return round(sum(1 for item in items if scenario_clean_passed(item)) / len(items), 6)

    return {
        "scenario_count": len(results),
        "tiers": dict(tiers),
        "origins": dict(origins),
        "criticalities": dict(criticalities),
        "golden_case_count": len(golden),
        "golden_pass_rate": pass_rate(golden),
        "golden_clean_pass_rate": clean_rate(golden),
        "critical_path_count": len(critical_path),
        "critical_path_pass_rate": pass_rate(critical_path),
        "critical_path_clean_pass_rate": clean_rate(critical_path),
        "failing_priority_cases": [
            {
                "id": result["id"],
                "bucket": result["bucket"],
                "status": result["status"],
                "criticality": result.get("case_metadata", {}).get("criticality"),
                "tier": result.get("case_metadata", {}).get("tier"),
                "origin": result.get("case_metadata", {}).get("origin"),
                "failure_reasons": [failure["reason"] for failure in result.get("failures", [])[:3]],
            }
            for result in failing_priority_cases[:5]
        ],
    }


def summarize_prune_candidates(results: list[dict], now: datetime) -> dict:
    candidates = []
    for result in results:
        if not scenario_clean_passed(result):
            continue
        metadata = result.get("case_metadata", {})
        stale_after_days = metadata.get("stale_after_days")
        if not isinstance(stale_after_days, int):
            continue
        reference_field, reference_dt, reference_raw = select_reference_timestamp(metadata)
        if reference_dt is None:
            continue
        days_since = (now - reference_dt).days
        if days_since < stale_after_days:
            continue
        candidates.append(
            {
                "id": result["id"],
                "bucket": result["bucket"],
                "tier": metadata.get("tier"),
                "origin": metadata.get("origin"),
                "criticality": metadata.get("criticality"),
                "days_since_reference": days_since,
                "stale_after_days": stale_after_days,
                "reference_field": reference_field,
                "reference_at": reference_raw,
            }
        )

    candidates.sort(
        key=lambda item: (
            -int(item["days_since_reference"]),
            item["id"],
        )
    )
    return {
        "scenario_count": len(candidates),
        "candidates": candidates[:10],
    }


def recommend_hardening_steps(
    results: list[dict], suite_health: dict, prune_candidates: dict, expand_mode_metrics: dict
) -> list[str]:
    recommendations = []
    failing_priority_cases = suite_health.get("failing_priority_cases", [])
    if failing_priority_cases:
        joined = ", ".join(case["id"] for case in failing_priority_cases[:3])
        recommendations.append(
            f"Fix failing golden or critical-path cases before broadening coverage: {joined}."
        )

    failure_classes = Counter()
    for result in results:
        metadata = result.get("case_metadata", {})
        failure_class = metadata.get("failure_class")
        if not failure_class or scenario_passed(result):
            continue
        failure_classes[str(failure_class)] += 1
    if failure_classes:
        top_failure_class, count = failure_classes.most_common(1)[0]
        recommendations.append(
            f"Turn the repeated `{top_failure_class}` pattern into the next targeted floor-raising hardening step ({count} failing case{'s' if count != 1 else ''})."
        )

    if suite_health.get("golden_case_count", 0) == 0:
        recommendations.append(
            "Add 3 to 5 golden must-not-break cases before expanding corpus coverage."
        )

    if suite_health.get("origins", {}).get("production_derived", 0) == 0:
        recommendations.append(
            "Capture the next reproduced real archive failure as a `production_derived` regression instead of only adding more corpus-derived coverage."
        )

    candidate_count = prune_candidates.get("scenario_count", 0)
    if candidate_count:
        joined = ", ".join(item["id"] for item in prune_candidates.get("candidates", [])[:3])
        recommendations.append(
            f"Review stale clean-pass cases for pruning or demotion: {joined}."
        )

    wrong_source_rate = expand_mode_metrics.get("wrong_source_rate")
    if isinstance(wrong_source_rate, float) and wrong_source_rate > 0:
        recommendations.append(
            "Tighten source-family enforcement in expand-mode scenarios before broadening the benchmark, because some first-run expansions still drift to disallowed sources."
        )

    query_failure_rate = expand_mode_metrics.get("query_efficiency_failure_rate")
    if isinstance(query_failure_rate, float) and query_failure_rate > 0:
        recommendations.append(
            "Harden question-shape search templates or refinement budgets, because expand-mode scenarios are still wasting queries inside the allowed source family."
        )

    if not recommendations:
        recommendations.append(
            "Keep the suite small and targeted: add only representative regressions, not speculative variants."
        )
    return recommendations


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
    now = datetime.now(timezone.utc)
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
    suite_health = summarize_suite_health(results)
    prune_candidates = summarize_prune_candidates(results, now)
    summary = {
        "passes_by_bucket": dict(by_bucket),
        "totals_by_bucket": dict(total_by_bucket),
        "common_failure_modes": failure_reasons.most_common(5),
        "suite_health": suite_health,
        "retrieval_metrics": summarize_metrics(results),
        "trajectory_metrics": summarize_trajectory(results),
        "answer_quality_metrics": summarize_answer_quality(results),
        "replay_metrics": summarize_replay_metrics(results),
        "expand_mode_metrics": summarize_expand_mode_metrics(results),
        "false_completion_metrics": summarize_false_completion_metrics(results),
        "prune_candidates": prune_candidates,
    }
    summary["recommended_hardening_steps"] = recommend_hardening_steps(
        results, suite_health, prune_candidates, summary["expand_mode_metrics"]
    )
    summary["thresholds"] = evaluate_thresholds(summary, load_thresholds(evals_root))
    report = {
        "generated_at": now.isoformat(),
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
            "expand_success_rate": summary.get("expand_mode_metrics", {}).get("expand_success_rate"),
            "wrong_source_rate": summary.get("expand_mode_metrics", {}).get("wrong_source_rate"),
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
        "| Example | Scenarios | hit@k | mrr@k | ndcg@k | completion | clean | drift | expand | wrong source | thresholds |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in examples:
        expand_success = row["expand_success_rate"]
        wrong_source = row["wrong_source_rate"]
        expand_success_text = f"{expand_success:.6f}" if isinstance(expand_success, float) else "n/a"
        wrong_source_text = f"{wrong_source:.6f}" if isinstance(wrong_source, float) else "n/a"
        lines.append(
            f"| `{row['example']}` | {row['scenario_count']} | {row['hit_at_k']:.6f} | {row['mrr_at_k']:.6f} | {row['ndcg_at_k']:.6f} | {row['completion_pass_rate']:.6f} | {row['clean_pass_rate']:.6f} | {row['drift_rate']:.6f} | {expand_success_text} | {wrong_source_text} | {'pass' if row['thresholds_ok'] else 'fail'} |"
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
