from __future__ import annotations

from datetime import date
from pathlib import Path

from ledger.archive_checks.runtime import (
    documents_by_id,
    entry_matches_term,
    load_json_file,
    load_yaml,
)


def dump_yaml(path: Path, payload: object) -> None:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PyYAML is required for recipe-backed checks. Re-run with `uv run python scripts/run_archive_check.py ...`."
        ) from exc
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding="utf-8")


def coverage_ledger_path(root: Path) -> Path:
    return root / "domain" / "coverage-ledger.yaml"


def load_coverage_ledger(root: Path) -> dict:
    coverage = load_yaml(coverage_ledger_path(root))
    if not isinstance(coverage, dict):
        coverage = {}
    coverage.setdefault("provisional_weak_slices", [])
    coverage.setdefault("partial_topics", [])
    coverage.setdefault("stale_topics", [])
    coverage.setdefault("support_gaps", [])
    coverage.setdefault("notes", [])
    return coverage


def save_coverage_ledger(root: Path, coverage: dict) -> None:
    dump_yaml(coverage_ledger_path(root), coverage)


def slugify_term(text: str) -> str:
    out = []
    for ch in text.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in {" ", "-", "_"}:
            out.append("_")
    slug = "".join(out).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "provisional_weak_slice"


def infer_current_support(root: Path, artifact_ids: list[str]) -> str | None:
    docs = documents_by_id(root)
    inferred = []
    for artifact_id in artifact_ids:
        artifact = docs.get(artifact_id, {})
        artifact_type = str(artifact.get("artifact_type", "")).strip()
        if artifact_type:
            inferred.append(artifact_type)
    if not inferred:
        return None
    if len(set(inferred)) == 1:
        return inferred[0]
    return "+".join(sorted(set(inferred)))


def append_coverage_note(coverage: dict, message: str) -> None:
    notes = coverage.setdefault("notes", [])
    if isinstance(notes, list) and message not in notes:
        notes.append(message)


def matching_provisional_entries(coverage: dict, term: str, task_type: str | None) -> list[dict]:
    normalized_term = term.strip()
    matched = []
    for entry in coverage.get("provisional_weak_slices", []):
        if not isinstance(entry, dict):
            continue
        task_types = entry.get("task_types")
        if isinstance(task_types, list) and task_type and task_type not in {str(item) for item in task_types}:
            continue
        if entry_matches_term(entry, normalized_term):
            matched.append(entry)
    return matched


def matching_support_gap_entries(coverage: dict, term: str, task_type: str | None) -> list[dict]:
    normalized_term = term.strip()
    matched = []
    for entry in coverage.get("support_gaps", []):
        if not isinstance(entry, dict):
            continue
        task_types = entry.get("task_types")
        if isinstance(task_types, list) and task_type and task_type not in {str(item) for item in task_types}:
            continue
        if entry_matches_term(entry, normalized_term):
            matched.append(entry)
    return matched


def register_provisional_weak_slice(root: Path, term: str | None, task_type: str | None, decision_payload: dict) -> dict:
    normalized_term = (term or "").strip()
    if not normalized_term:
        return {
            "ok": False,
            "check": "register_provisional_weak_slice",
            "summary": "term is required to register provisional weak slice",
            "failures": [{"reason": "provide --term"}],
        }
    coverage = load_coverage_ledger(root)
    if matching_support_gap_entries(coverage, normalized_term, task_type):
        return {
            "ok": True,
            "check": "register_provisional_weak_slice",
            "summary": "matching support gap already exists; provisional registration skipped",
            "status": "existing_confirmed_gap",
            "counts": {"created": 0},
            "failures": [],
        }
    if matching_provisional_entries(coverage, normalized_term, task_type):
        return {
            "ok": True,
            "check": "register_provisional_weak_slice",
            "summary": "matching provisional weak slice already exists",
            "status": "existing_provisional",
            "counts": {"created": 0},
            "failures": [],
        }

    action = str(decision_payload.get("action", "")).lower()
    if action != "expand":
        return {
            "ok": False,
            "check": "register_provisional_weak_slice",
            "summary": "only expand decisions can register provisional weak slices",
            "failures": [{"reason": f"decision action must be expand, got {action or 'missing'}"}],
        }

    quality_status = str(decision_payload.get("quality_status", "")).lower()
    if quality_status and quality_status not in {"provisional", "below_target"}:
        return {
            "ok": False,
            "check": "register_provisional_weak_slice",
            "summary": "decision quality status does not justify provisional registration",
            "failures": [{"reason": f"unsupported quality_status: {quality_status}"}],
        }

    artifact_ids = [str(item).strip() for item in decision_payload.get("artifact_ids", []) if str(item).strip()]
    current_support = str(decision_payload.get("current_support", "")).strip() or infer_current_support(root, artifact_ids)
    source_family = str(decision_payload.get("source_family", "")).strip()
    reason = str(decision_payload.get("reason", "")).strip()
    if not reason:
        return {
            "ok": False,
            "check": "register_provisional_weak_slice",
            "summary": "decision reason is required for provisional registration",
            "failures": [{"reason": "decision reason missing"}],
        }

    labels = [normalized_term]
    for item in decision_payload.get("match_terms", []):
        label = str(item).strip()
        if label and label not in labels:
            labels.append(label)
    notes = [
        f"Registered automatically from expand decision on {date.today().isoformat()}.",
        "This provisional slice should be confirmed, cleared, or superseded after later enrichment.",
    ]
    for item in decision_payload.get("notes", []):
        note = str(item).strip()
        if note and note not in notes:
            notes.append(note)
    entry = {
        "topic": str(decision_payload.get("topic", "")).strip() or slugify_term(normalized_term),
        "labels": labels,
        "task_types": [task_type] if task_type else [],
        "suspected_support_gap": str(decision_payload.get("suspected_support_gap", "")).strip() or "suspected_weak_slice",
        "current_support": current_support or "unknown",
        "reason": reason,
        "source_family": source_family or "unknown",
        "artifact_ids": artifact_ids,
        "notes": notes,
    }
    coverage.setdefault("provisional_weak_slices", []).append(entry)
    save_coverage_ledger(root, coverage)
    return {
        "ok": True,
        "check": "register_provisional_weak_slice",
        "summary": "provisional weak slice registered",
        "status": "created",
        "counts": {"created": 1},
        "entry": entry,
        "failures": [],
    }


def resolve_provisional_weak_slice(
    root: Path,
    term: str | None,
    task_type: str | None,
    resolution: str | None,
    resolution_payload: dict | None,
) -> dict:
    normalized_term = (term or "").strip()
    outcome = str(resolution or "").strip().lower()
    if not normalized_term:
        return {
            "ok": False,
            "check": "resolve_provisional_weak_slice",
            "summary": "term is required to resolve provisional weak slice",
            "failures": [{"reason": "provide --term"}],
        }
    if outcome not in {"confirmed", "cleared", "superseded"}:
        return {
            "ok": False,
            "check": "resolve_provisional_weak_slice",
            "summary": "resolution must be confirmed, cleared, or superseded",
            "failures": [{"reason": f"unsupported resolution: {resolution}"}],
        }

    coverage = load_coverage_ledger(root)
    matched = matching_provisional_entries(coverage, normalized_term, task_type)
    if not matched:
        return {
            "ok": False,
            "check": "resolve_provisional_weak_slice",
            "summary": "no matching provisional weak slice found",
            "failures": [{"reason": "no matching provisional weak slice"}],
        }

    payload = resolution_payload or {}
    target = matched[0]
    coverage["provisional_weak_slices"] = [
        entry for entry in coverage.get("provisional_weak_slices", []) if entry is not target
    ]
    note = str(payload.get("note", "")).strip()
    dated_note = f"{outcome.title()} provisional weak slice `{target.get('topic', normalized_term)}` on {date.today().isoformat()}."
    if note:
        dated_note = f"{dated_note} {note}"

    if outcome == "confirmed":
        answer_contract = load_yaml(root / "recipes" / "answer-contract.yaml")
        support_targets = answer_contract.get("support_targets", {}) if isinstance(answer_contract, dict) else {}
        required_support = (
            str(payload.get("required_support", "")).strip()
            or support_targets.get(task_type or "", support_targets.get("rule_lookup"))
            or "extract"
        )
        support_gap = {
            "topic": target.get("topic"),
            "labels": target.get("labels", []),
            "task_types": target.get("task_types", [task_type] if task_type else []),
            "required_support": required_support,
            "current_support": payload.get("current_support") or target.get("current_support", "unknown"),
            "quality_status": "below_target",
            "follow_up_action": str(payload.get("follow_up_action", "")).strip() or "expand",
            "source_family": target.get("source_family", "unknown"),
            "artifact_ids": target.get("artifact_ids", []),
            "notes": list(target.get("notes", [])) + [dated_note],
        }
        coverage.setdefault("support_gaps", []).append(support_gap)
        save_coverage_ledger(root, coverage)
        return {
            "ok": True,
            "check": "resolve_provisional_weak_slice",
            "summary": "provisional weak slice confirmed and promoted to support gap",
            "status": "confirmed",
            "counts": {"resolved": 1},
            "entry": support_gap,
            "failures": [],
        }

    append_coverage_note(coverage, dated_note)
    save_coverage_ledger(root, coverage)
    return {
        "ok": True,
        "check": "resolve_provisional_weak_slice",
        "summary": f"provisional weak slice {outcome}",
        "status": outcome,
        "counts": {"resolved": 1},
        "failures": [],
    }


def load_resolution_payload(path: Path | None) -> dict | None:
    return load_json_file(path) if path else None
