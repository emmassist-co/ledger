from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml


CURRENTNESS_HINTS = {
    "current",
    "currently",
    "latest",
    "newest",
    "today",
    "recent",
    "recently",
    "last",
    "updated",
    "update",
    "still",
    "now",
}

GENERIC_QUERY_TOKENS = {
    "a",
    "an",
    "and",
    "are",
    "archive",
    "about",
    "for",
    "from",
    "how",
    "in",
    "is",
    "know",
    "law",
    "laws",
    "latest",
    "last",
    "newest",
    "now",
    "of",
    "on",
    "published",
    "question",
    "recent",
    "recently",
    "rule",
    "rules",
    "the",
    "this",
    "today",
    "updated",
    "what",
    "when",
    "where",
    "which",
}

AUDIT_HINTS = (
    "audit",
    "review this answer",
    "review the answer",
    "verify this answer",
    "verify the answer",
    "did the archive",
    "did the agent",
)

CASE_APPLICATION_PATTERNS = (
    r"\bmy\b",
    r"\bme\b",
    r"\bmine\b",
    r"\bour\b",
    r"\bwe\b",
    r"\bus\b",
    r"\bi\b",
    r"\bfor me\b",
    r"\bfor us\b",
    r"\bmy company\b",
    r"\bour company\b",
    r"\bam i\b",
    r"\bcan i\b",
    r"\bdo i\b",
    r"\bdoes my\b",
    r"\bdoes our\b",
)


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
        stripped = line.strip()
        if stripped:
            rows.append(json.loads(stripped))
    return rows


def tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"[^0-9a-z]+", text.lower()) if token]


def meaningful_query_tokens(question: str) -> list[str]:
    return [token for token in tokenize(question) if token not in GENERIC_QUERY_TOKENS]


def slugify(text: str) -> str:
    parts = []
    for ch in text.lower():
        if ch.isalnum():
            parts.append(ch)
        elif ch in {" ", "-", "_"}:
            parts.append("-")
    slug = "".join(parts).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "question"


def classify_question(question: str) -> str:
    lowered = question.lower()
    if any(hint in lowered for hint in AUDIT_HINTS):
        return "archive_audit"
    if any(re.search(pattern, lowered) for pattern in CASE_APPLICATION_PATTERNS):
        return "case_application"
    return "rule_lookup"


def current_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_fact_intake(archive_root: Path) -> dict:
    path = archive_root / "recipes" / "fact-intake.yaml"
    if not path.exists():
        return {}
    return read_yaml(path)


def load_currentness_rules(archive_root: Path) -> dict:
    path = archive_root / "recipes" / "currentness-rules.yaml"
    if not path.exists():
        return {}
    return read_yaml(path)


def load_freshness_state(archive_root: Path) -> dict:
    path = archive_root / "artifacts" / "state" / "source-freshness.json"
    if not path.exists():
        return {"schema_version": 1, "families": {}}
    return read_json(path)


def build_archive_state_summary(archive_root: Path) -> dict:
    freshness = load_freshness_state(archive_root)
    documents = iter_jsonl(archive_root / "index" / "documents.jsonl")
    families = freshness.get("families", {})
    freshness_ok = 0
    if isinstance(families, dict):
        freshness_ok = sum(1 for state in families.values() if isinstance(state, dict) and state.get("last_sync_ok"))
    summary = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "archive_root": str(archive_root),
        "document_count": len(documents),
        "has_domain_pack": (archive_root / "recipes" / "domain-profile.yaml").exists(),
        "has_archive_checks": (archive_root / "scripts" / "run_archive_check.py").exists(),
        "has_currentness_rules": (archive_root / "recipes" / "currentness-rules.yaml").exists(),
        "freshness_family_count": len(families) if isinstance(families, dict) else 0,
        "freshness_ok_family_count": freshness_ok,
        "archive_evals_present": (archive_root / "archive-evals" / "manifest.json").exists(),
    }
    write_json(archive_root / "artifacts" / "state" / "archive-state-summary.json", summary)
    return summary


def find_candidate_artifacts(archive_root: Path, question: str, limit: int = 5) -> list[dict]:
    tokens = meaningful_query_tokens(question)
    if not tokens:
        return []
    docs = iter_jsonl(archive_root / "index" / "documents.jsonl")
    scored = []
    question_lower = question.lower()
    for row in docs:
        search_text = " ".join(
            str(row.get(field, ""))
            for field in ("title", "search_text", "artifact_id", "source_url")
        ).lower()
        if not search_text.strip():
            continue
        exact_bonus = 3 if question_lower and question_lower in search_text else 0
        token_hits = sum(1 for token in tokens if token and token in search_text)
        score = exact_bonus + token_hits
        if score <= 0:
            continue
        scored.append(
            (
                score,
                {
                    "artifact_id": row.get("artifact_id"),
                    "title": row.get("title") or row.get("artifact_id"),
                    "artifact_type": row.get("artifact_type"),
                    "path": row.get("path"),
                    "source_url": row.get("source_url"),
                    "score": score,
                },
            )
        )
    scored.sort(key=lambda item: (-item[0], str(item[1].get("artifact_id") or "")))
    return [payload for _, payload in scored[:limit]]


def infer_support_state(candidates: list[dict]) -> str:
    if not candidates:
        return "none"
    top_score = int(candidates[0].get("score") or 0)
    if top_score >= 2:
        return "grounded"
    return "partial"


def infer_currentness_sensitivity(question: str) -> bool:
    tokens = tokenize(question)
    return any(token in CURRENTNESS_HINTS for token in tokens)


def infer_currentness_state(archive_root: Path, currentness_sensitive: bool) -> str:
    if not currentness_sensitive:
        return "not_requested"
    rules = load_currentness_rules(archive_root)
    freshness = load_freshness_state(archive_root)
    if not rules.get("enabled"):
        return "unconfigured"
    families = freshness.get("families", {})
    if not isinstance(families, dict) or not families:
        return "missing"
    if any(isinstance(state, dict) and state.get("last_sync_ok") for state in families.values()):
        return "available"
    return "missing"


def missing_required_facts(archive_root: Path, question_shape: str, user_facts: dict[str, object]) -> list[str]:
    if question_shape != "case_application":
        return []
    fact_intake = load_fact_intake(archive_root)
    required = fact_intake.get("required_facts", [])
    if not isinstance(required, list):
        return []
    missing = []
    for entry in required:
        if not isinstance(entry, dict):
            continue
        fact_id = str(entry.get("fact_id") or "").strip()
        required_for = entry.get("required_for")
        if not fact_id:
            continue
        if isinstance(required_for, list) and question_shape not in {str(item) for item in required_for}:
            continue
        if fact_id not in user_facts:
            missing.append(fact_id)
    return missing


def run_coverage_state_check(archive_root: Path, question: str, question_shape: str) -> dict | None:
    helper = archive_root / "scripts" / "run_archive_check.py"
    if not helper.exists():
        return None
    completed = subprocess.run(
        [
            sys.executable,
            str(helper),
            "check_coverage_state",
            "--archive-root",
            str(archive_root),
            "--term",
            question,
            "--task-type",
            question_shape,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if not completed.stdout.strip():
        return None
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "check": "check_coverage_state",
            "summary": "coverage state payload unreadable",
            "failures": [{"reason": "invalid helper JSON"}],
        }
    payload["exit_code"] = completed.returncode
    return payload


def decide_outcome(
    question_shape: str,
    support_state: str,
    currentness_sensitive: bool,
    currentness_state: str,
    missing_facts: list[str],
    coverage_state: dict | None,
) -> tuple[str, list[str]]:
    reasons = []
    if missing_facts:
        reasons.append("case application is missing required user facts")
        return "ask_user", reasons
    if support_state == "none":
        reasons.append("archive has no matching local support for this question")
        return "expand", reasons
    if coverage_state and coverage_state.get("ok") is False:
        reasons.append("coverage-state gate reports below-target or partial support")
        return "expand", reasons
    if currentness_sensitive and support_state != "grounded":
        reasons.append("currentness-sensitive question needs more specific local support")
        return "expand", reasons
    if currentness_state in {"missing", "unconfigured"}:
        reasons.append("currentness-sensitive question lacks usable freshness state")
        return "expand", reasons
    if question_shape == "archive_audit" and support_state == "partial":
        reasons.append("audit question found partial support but no stronger local trail")
        return "expand", reasons
    reasons.append("local support and state are sufficient for the operator to answer")
    return "decisive_answer", reasons


@dataclass
class ConsultationResult:
    payload: dict
    audit_path: Path


def consult_archive(
    archive_root: Path,
    question: str,
    *,
    question_shape: str | None = None,
    user_facts: dict[str, object] | None = None,
    output_path: Path | None = None,
) -> ConsultationResult:
    archive_root = archive_root.resolve()
    resolved_shape = question_shape or classify_question(question)
    resolved_facts = user_facts or {}
    state_summary = build_archive_state_summary(archive_root)
    candidates = find_candidate_artifacts(archive_root, question)
    support_state = infer_support_state(candidates)
    currentness_sensitive = infer_currentness_sensitivity(question)
    currentness_state = infer_currentness_state(archive_root, currentness_sensitive)
    missing_facts = missing_required_facts(archive_root, resolved_shape, resolved_facts)
    coverage_state = run_coverage_state_check(archive_root, question, resolved_shape)
    outcome, reasons = decide_outcome(
        resolved_shape,
        support_state,
        currentness_sensitive,
        currentness_state,
        missing_facts,
        coverage_state,
    )

    timestamp = current_timestamp()
    audit_payload = {
        "schema_version": 1,
        "consultation_runtime_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "archive_root": str(archive_root),
        "question": question,
        "question_shape": resolved_shape,
        "user_facts": resolved_facts,
        "missing_user_facts": missing_facts,
        "support_state": support_state,
        "currentness_sensitive": currentness_sensitive,
        "currentness_state": currentness_state,
        "candidate_artifacts": candidates,
        "coverage_state": coverage_state,
        "archive_state_summary": state_summary,
        "outcome": outcome,
        "outcome_reasons": reasons,
        "recommended_next_step": (
            "provide missing facts"
            if outcome == "ask_user"
            else "expand archive support from canonical sources"
            if outcome == "expand"
            else "operator can answer from local archive support"
        ),
    }
    if output_path is None:
        output_path = (
            archive_root
            / "artifacts"
            / "state"
            / "consultations"
            / f"{timestamp}-{slugify(question)[:48]}.json"
        )
    write_json(output_path, audit_payload)
    return ConsultationResult(payload=audit_payload, audit_path=output_path)


def load_user_facts(args: argparse.Namespace) -> dict[str, object]:
    if args.facts_json:
        payload = read_json(Path(args.facts_json))
    elif args.facts_payload:
        payload = json.loads(args.facts_payload)
    else:
        return {}
    if not isinstance(payload, dict):
        raise ValueError("user facts payload must be a JSON object")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="consult_archive")
    parser.add_argument("--archive-root", type=Path, default=Path("."))
    parser.add_argument("--question", required=True)
    parser.add_argument("--question-shape", choices=["rule_lookup", "case_application", "archive_audit"])
    parser.add_argument("--facts-json")
    parser.add_argument("--facts-payload")
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:] if argv is not None else None)
    try:
        user_facts = load_user_facts(args)
    except (ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "reason": str(exc)}))
        return 2
    result = consult_archive(
        args.archive_root,
        args.question,
        question_shape=args.question_shape,
        user_facts=user_facts,
        output_path=args.output,
    )
    payload = dict(result.payload)
    payload["audit_path"] = str(result.audit_path)
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0
