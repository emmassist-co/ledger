from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_policy(root: Path) -> dict:
    policy_path = root / "config" / "index-policy.yaml"
    return {
        "policy_path": str(policy_path),
        "exists": policy_path.exists(),
    }


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def emit(payload: dict) -> int:
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if payload.get("ok") else 1


def policy_allowed_values(root: Path) -> dict[str, set[str]]:
    policy_text = (root / "config" / "index-policy.yaml").read_text(encoding="utf-8")
    groups: dict[str, set[str]] = {}
    current = None
    for line in policy_text.splitlines():
        stripped = line.strip()
        if stripped.endswith(":") and not stripped.startswith("-"):
            current = stripped[:-1]
            continue
        if current and stripped.startswith("- "):
            groups.setdefault(current, set()).add(stripped[2:])
    return groups


def check_coverage(root: Path, args: argparse.Namespace) -> int:
    docs = iter_jsonl(root / "index" / "documents.jsonl")
    links = iter_jsonl(root / "index" / "links.jsonl")
    candidates = docs
    if args.term:
        term = args.term.lower()
        candidates = [
            row for row in docs
            if term in (row.get("title", "") + " " + row.get("search_text", "")).lower()
        ]
    return emit({
        "ok": bool(candidates),
        "check": "check_coverage",
        "summary": "matching artifacts found" if candidates else "no matching artifacts found",
        "counts": {
            "documents": len(docs),
            "links": len(links),
            "candidates": len(candidates),
        },
        "failures": [] if candidates else [{"reason": "no candidate artifacts for requested term"}],
    })


def check_provenance(root: Path, args: argparse.Namespace) -> int:
    failures = []
    checked = 0
    for row in iter_jsonl(root / "index" / "documents.jsonl"):
        checked += 1
        if not row.get("source_url"):
            failures.append({"artifact_id": row.get("artifact_id"), "reason": "missing source_url"})
        path = row.get("path")
        if path and not Path(path).exists():
            failures.append({"artifact_id": row.get("artifact_id"), "reason": "artifact path missing on disk"})
    return emit({
        "ok": not failures,
        "check": "check_provenance",
        "summary": "all checked artifacts have basic provenance" if not failures else "provenance failures found",
        "counts": {
            "artifacts_checked": checked,
            "failures": len(failures),
        },
        "failures": failures,
    })


def check_policy(root: Path, args: argparse.Namespace) -> int:
    policy = load_policy(root)
    failures = []
    if not policy["exists"]:
        failures.append({"reason": "missing config/index-policy.yaml"})
    if args.action == "expand" and args.autonomy_policy == "ask-first":
        failures.append({"reason": "policy blocks automatic expansion in ask-first mode"})
    return emit({
        "ok": not failures,
        "check": "check_policy",
        "summary": "policy allows requested action" if not failures else "policy blocks requested action",
        "counts": {
            "failures": len(failures),
        },
        "failures": failures,
    })


def check_decision_record(root: Path, args: argparse.Namespace) -> int:
    record = load_json(Path(args.decision_json))
    allowed = policy_allowed_values(root)
    failures = []
    required = ["action", "reason", "source_type", "scope_status", "artifact_kind"]
    for key in required:
        if not record.get(key):
            failures.append({"field": key, "reason": "missing required field"})
    if record.get("action") and record["action"] not in allowed.get("allowed_actions", set()):
        failures.append({"field": "action", "reason": "disallowed action"})
    if record.get("source_type") and record["source_type"] not in allowed.get("allowed_source_types", set()):
        failures.append({"field": "source_type", "reason": "disallowed source_type"})
    if record.get("scope_status") and record["scope_status"] not in allowed.get("allowed_scope_statuses", set()):
        failures.append({"field": "scope_status", "reason": "disallowed scope_status"})
    if record.get("artifact_kind") and record["artifact_kind"] not in allowed.get("allowed_artifact_kinds", set()):
        failures.append({"field": "artifact_kind", "reason": "disallowed artifact_kind"})
    if record.get("action") == "skip_persist":
        skip_reason = record.get("skip_reason")
        if not skip_reason:
            failures.append({"field": "skip_reason", "reason": "required for skip_persist"})
        elif skip_reason not in allowed.get("allowed_skip_reasons", set()):
            failures.append({"field": "skip_reason", "reason": "disallowed skip_reason"})
    return emit({
        "ok": not failures,
        "check": "check_decision_record",
        "summary": "decision record accepted" if not failures else "decision record blocked",
        "counts": {"failures": len(failures)},
        "failures": failures,
    })


def check_claim_support(root: Path, args: argparse.Namespace) -> int:
    payload = load_json(Path(args.claims_json))
    failures = []
    supported = 0
    for claim in payload.get("claims", []):
        evidence_ids = claim.get("evidence_ids", [])
        if evidence_ids:
            supported += 1
        else:
            failures.append({
                "claim_id": claim.get("claim_id"),
                "reason": "no evidence_ids provided",
            })
    return emit({
        "ok": not failures,
        "check": "check_claim_support",
        "summary": "all claims have evidence ids" if not failures else "some claims lack evidence ids",
        "counts": {
            "claims_checked": len(payload.get("claims", [])),
            "claims_supported": supported,
            "failures": len(failures),
        },
        "failures": failures,
    })


def check_exact_wording(root: Path, args: argparse.Namespace) -> int:
    payload = load_json(Path(args.claims_json))
    failures = []
    checked = 0
    for claim in payload.get("claims", []):
        if not claim.get("exact_wording"):
            continue
        checked += 1
        support_kind = claim.get("support_kind")
        if support_kind not in {"raw_source", "extract"}:
            failures.append({
                "claim_id": claim.get("claim_id"),
                "reason": "exact wording requires raw_source or extract support",
            })
    return emit({
        "ok": not failures,
        "check": "check_exact_wording",
        "summary": "exact-wording claims have sufficient support" if not failures else "exact-wording claims blocked",
        "counts": {"claims_checked": checked, "failures": len(failures)},
        "failures": failures,
    })


def rebuild_index(root: Path, args: argparse.Namespace) -> int:
    artifacts = sorted(root.glob("artifacts/**/*.md"))
    links_path = root / "index" / "links.jsonl"
    docs_path = root / "index" / "documents.jsonl"
    root.joinpath("index").mkdir(parents=True, exist_ok=True)
    if not docs_path.exists():
        docs_path.write_text("", encoding="utf-8")
    if not links_path.exists():
        links_path.write_text("", encoding="utf-8")
    return emit({
        "ok": True,
        "check": "rebuild_index",
        "summary": "index placeholders verified; implement corpus-specific rebuild as needed",
        "counts": {
            "artifact_markdown_files": len(artifacts),
        },
        "failures": [],
    })


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=[
        "check_coverage",
        "check_provenance",
        "check_policy",
        "check_decision_record",
        "check_claim_support",
        "check_exact_wording",
        "rebuild_index",
    ])
    parser.add_argument("archive_root")
    parser.add_argument("--term")
    parser.add_argument("--action", default="answer")
    parser.add_argument("--autonomy-policy", default="proactive")
    parser.add_argument("--claims-json")
    parser.add_argument("--decision-json")
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    root = Path(args.archive_root).resolve()
    handlers = {
        "check_coverage": check_coverage,
        "check_provenance": check_provenance,
        "check_policy": check_policy,
        "check_decision_record": check_decision_record,
        "check_claim_support": check_claim_support,
        "check_exact_wording": check_exact_wording,
        "rebuild_index": rebuild_index,
    }
    if args.command == "check_claim_support" and not args.claims_json:
        parser.error("--claims-json is required for check_claim_support")
    if args.command == "check_exact_wording" and not args.claims_json:
        parser.error("--claims-json is required for check_exact_wording")
    if args.command == "check_decision_record" and not args.decision_json:
        parser.error("--decision-json is required for check_decision_record")
    return handlers[args.command](root, args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
