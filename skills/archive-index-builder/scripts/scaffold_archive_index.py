from __future__ import annotations

import sys
from pathlib import Path


README = """# Archive Index Workspace

This workspace is a cheap-first retrieval scaffold for large archives.

Start with:

- `config/index-policy.yaml`
- `sql/schema.sql`
- `docs/promotion-rules.md`
- `scripts/archive_verifier.py`
- `scripts/rebuild_index.py`
- `scripts/check_index_consistency.py`

After the archive is usable, validate it with the separate `archive-evals` companion skill.

Build in layers:

- `source/downloads/`: saved canonical source files
- `source/manifests/`: acquisition metadata and hashes
- `artifacts/registry/`: one entry per source document
- `artifacts/extracts/`: verbatim or deterministic extract units
- `artifacts/derived/`: summaries, crosswalks, claims, entities, resolutions

Do not let LLM-authored artifacts become the only surviving representation of source text.
Do not hand-edit derived index outputs. Rebuild them from source artifacts.
"""


INDEX_POLICY = """tiers:
  l0:
    description: Global registry, source preservation, and cheap routing metadata
    required_fields:
      - doc_id
      - source_url
      - date
      - corpus
      - source_local_path
      - source_hash
  l1:
    description: Verbatim or deterministic extract units for shortlisted documents
  l2:
    description: Claims, references, entities, evidence pointers, and derived summaries
  l3:
    description: Canonical source resolution

operating_mode:
  default: balanced
  recommended_for:
    legal: accuracy_first
    regulatory: accuracy_first
    medical: accuracy_first
    financial: accuracy_first
    general_documents: balanced
    exploratory_research: speed_first

verifier_policy:
  required_checks:
    - check_coverage
    - check_provenance
    - check_policy
    - check_decision_record
  require_claim_support_for_decisive_answers: true
  require_extract_evidence_in_accuracy_mode: true
  block_exact_wording_without_raw_or_extract: true

decision_record_policy:
  required_for_actions:
    - expand
    - persist
    - skip_persist
  allowed_actions:
    - answer
    - expand
    - persist
    - skip_persist
    - ask_user
  allowed_source_types:
    - official
    - unofficial
  allowed_scope_statuses:
    - in_bounds
    - out_of_bounds
    - insufficient_input
  allowed_artifact_kinds:
    - canonical
    - reusable
    - ad_hoc
    - extract
    - derived_summary
    - annual_values
    - crosswalk
    - resolution
    - calculation
    - temporary_case_note
    - user_specific
  allowed_skip_reasons:
    - duplicate
    - transient_page
    - out_of_scope
    - user_specific
    - insufficient_value
    - policy_blocked

promotion:
  to_l1:
    - repeated_query_hits
    - topic_is_hot
    - summary_points_to_specific_block
  to_l2:
    - answer_requires_claim_extraction
    - answer_requires_reference_normalization
  to_l3:
    - answer_requires_canonical_source

query_order:
  - metadata_filter
  - extract_level_search
  - keyword_search
  - rerank_candidates
  - open_candidate_blocks
  - promote_if_reused
"""


SCHEMA = """create table if not exists documents (
    doc_id text primary key,
    corpus text not null,
    title text,
    source_url text not null,
    source_local_path text,
    source_hash text,
    document_number text,
    legislature text,
    session text,
    published_on text,
    page_count integer,
    raw_text_path text,
    summary_text text,
    tier text not null default 'l0'
);

create table if not exists extracts (
    extract_id text primary key,
    doc_id text not null references documents(doc_id),
    extract_type text,
    title text,
    article_number text,
    speaker text,
    party text,
    pointer text,
    page_start integer,
    page_end integer,
    text_path text,
    verbatim_status text not null default 'deterministic_extract',
    tier text not null default 'l1'
);

create table if not exists derived_artifacts (
    artifact_id text primary key,
    doc_id text references documents(doc_id),
    artifact_type text not null,
    title text,
    source_extract_id text references extracts(extract_id),
    path text not null,
    confidence text,
    tier text not null default 'l2'
);

create table if not exists query_hits (
    query_hash text not null,
    target_id text not null,
    target_type text not null,
    hit_count integer not null default 1,
    primary key (query_hash, target_id, target_type)
);
"""


PROMOTION_RULES = """# Promotion Rules

## L0 to L1

- Document appears in repeated query results
- A concrete question depends on exact wording
- Summary text points to a narrow intervention, article, or debate block
- Topic becomes part of an active workstream

## L1 to L2

- Block is reused often
- Answer depends on extracting claims or references
- Users need evidence cards instead of raw text

## L2 to L3

- Block references a law, initiative, vote, report, or programme that must be linked canonically
- High-stakes answer requires stronger provenance
"""


VERIFIER_SCRIPT = r'''from __future__ import annotations

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


def tokenize(text: str) -> list[str]:
    token = []
    tokens = []
    for ch in text.lower():
        if ch.isalnum():
            token.append(ch)
        elif token:
            tokens.append("".join(token))
            token = []
    if token:
        tokens.append("".join(token))
    return tokens


def infer_support_kind(claim: dict, documents_by_id: dict[str, dict]) -> str | None:
    support_kind = claim.get("support_kind") or claim.get("support_type")
    if support_kind:
        return str(support_kind)
    evidence_ids = claim.get("evidence_ids", [])
    inferred = []
    for artifact_id in evidence_ids:
        artifact = documents_by_id.get(artifact_id, {})
        artifact_type = artifact.get("artifact_type")
        if artifact_type == "extract":
            inferred.append("extract")
        elif artifact_type in {"raw_source", "source_document"}:
            inferred.append("raw_source")
        elif artifact_type:
            inferred.append("derived_summary")
    if "raw_source" in inferred:
        return "raw_source"
    if "extract" in inferred:
        return "extract"
    if "derived_summary" in inferred:
        return "derived_summary"
    return None


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
        term_tokens = tokenize(term)
        scored = []
        for row in docs:
            haystack = (row.get("title", "") + " " + row.get("search_text", "")).lower()
            if term in haystack:
                scored.append((len(term_tokens) + 1, row))
                continue
            token_hits = sum(1 for token in term_tokens if token and token in haystack)
            if token_hits:
                scored.append((token_hits, row))
        scored.sort(key=lambda pair: (-pair[0], pair[1].get("artifact_id", "")))
        candidates = [row for _, row in scored]
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
    action = record.get("action")
    required = ["action", "reason", "source_type", "scope_status"]
    if action != "ask_user":
        required.append("artifact_kind")
    for key in required:
        if not record.get(key):
            failures.append({"field": key, "reason": "missing required field"})
    if action and action not in allowed.get("allowed_actions", set()):
        failures.append({"field": "action", "reason": "disallowed action"})
    if record.get("source_type") and record["source_type"] not in allowed.get("allowed_source_types", set()):
        failures.append({"field": "source_type", "reason": "disallowed source_type"})
    if record.get("scope_status") and record["scope_status"] not in allowed.get("allowed_scope_statuses", set()):
        failures.append({"field": "scope_status", "reason": "disallowed scope_status"})
    if record.get("artifact_kind") and record["artifact_kind"] not in allowed.get("allowed_artifact_kinds", set()):
        failures.append({"field": "artifact_kind", "reason": "disallowed artifact_kind"})
    if action == "ask_user" and not record.get("artifact_kind"):
        record["artifact_kind"] = "user_specific"
    if action == "skip_persist":
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
    documents_by_id = {row.get("artifact_id"): row for row in iter_jsonl(root / "index" / "documents.jsonl")}
    for claim in payload.get("claims", []):
        evidence_ids = claim.get("evidence_ids", [])
        if not evidence_ids:
            failures.append({
                "claim_id": claim.get("claim_id"),
                "reason": "no evidence_ids provided",
            })
            continue
        missing_ids = [artifact_id for artifact_id in evidence_ids if artifact_id not in documents_by_id]
        if missing_ids:
            failures.append({
                "claim_id": claim.get("claim_id"),
                "reason": "evidence_ids not present in archive index",
                "missing_evidence_ids": missing_ids,
            })
            continue
        supported += 1
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
    documents_by_id = {row.get("artifact_id"): row for row in iter_jsonl(root / "index" / "documents.jsonl")}
    for claim in payload.get("claims", []):
        if not claim.get("exact_wording"):
            continue
        checked += 1
        support_kind = infer_support_kind(claim, documents_by_id)
        if support_kind not in {"raw_source", "extract"}:
            failures.append({
                "claim_id": claim.get("claim_id"),
                "reason": "exact wording requires raw_source or extract support",
                "support_kind": support_kind,
            })
    if payload.get("claims") and checked == 0:
        failures.append({"reason": "no exact_wording claims were supplied"})
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
'''


REBUILD_SCRIPT = r'''from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "artifacts"
INDEX_DIR = ROOT / "index"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    data = {}
    current_key = None
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- ") and current_key:
            data.setdefault(current_key, [])
            data[current_key].append(stripped[2:].strip())
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        value = value.strip()
        data[current_key] = [] if value == "" else value
    return data, body


def first_heading(body: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def build_search_text(meta: dict, body: str) -> str:
    fields = []
    for key in ("artifact_type", "artifact_id", "title", "source_title", "doc_id", "speaker", "party", "source_url", "source_parent_url", "section_id", "article_number", "number", "label"):
        value = meta.get(key)
        if isinstance(value, str) and value:
            fields.append(value)
    linked = meta.get("linked_ids")
    if isinstance(linked, list):
        fields.extend(str(item) for item in linked)
    fields.append(body)
    return compact_text(" ".join(fields))


def collect_artifacts():
    documents = []
    links = []
    for path in sorted(ARTIFACTS_DIR.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        artifact_id = str(meta.get("artifact_id", "")).strip()
        if not artifact_id:
            continue
        title = str(meta.get("title", "")).strip() or first_heading(body) or artifact_id
        documents.append({
            "artifact_id": artifact_id,
            "artifact_type": str(meta.get("artifact_type", "")).strip(),
            "path": str(path.resolve()),
            "title": title,
            "source_system": str(meta.get("source_system", "")).strip(),
            "source_url": str(meta.get("source_url", "")).strip(),
            "normalized_date": str(meta.get("normalized_date", "")).strip(),
            "doc_id": str(meta.get("doc_id", "")).strip(),
            "confidence": str(meta.get("confidence", "")).strip(),
            "search_text": build_search_text(meta, body),
        })
        linked_ids = meta.get("linked_ids")
        if isinstance(linked_ids, list):
            for linked_id in linked_ids:
                links.append({"from_id": artifact_id, "to_id": str(linked_id), "relationship": "linked", "path": str(path.resolve())})
    return documents, links


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_sqlite(path: Path, documents, links):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    try:
        conn.execute("create table documents (artifact_id text primary key, artifact_type text, path text, title text, source_system text, source_url text, normalized_date text, doc_id text, confidence text, search_text text)")
        conn.execute("create table links (from_id text, to_id text, relationship text, path text)")
        conn.execute("create virtual table documents_fts using fts5(artifact_id, title, search_text)")
        conn.executemany("insert into documents values (:artifact_id, :artifact_type, :path, :title, :source_system, :source_url, :normalized_date, :doc_id, :confidence, :search_text)", documents)
        conn.executemany("insert into links values (:from_id, :to_id, :relationship, :path)", links)
        conn.executemany("insert into documents_fts values (:artifact_id, :title, :search_text)", documents)
        conn.commit()
    finally:
        conn.close()


def main():
    argparse.ArgumentParser().parse_args()
    documents, links = collect_artifacts()
    write_jsonl(INDEX_DIR / "documents.jsonl", documents)
    write_jsonl(INDEX_DIR / "links.jsonl", links)
    write_sqlite(INDEX_DIR / "navigation.sqlite", documents, links)
    print(json.dumps({"ok": True, "documents": len(documents), "links": len(links)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


CONSISTENCY_SCRIPT = r'''from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from rebuild_index import collect_artifacts, write_jsonl


ROOT = Path(__file__).resolve().parents[1]


def read_lines(path: Path):
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def main():
    argparse.ArgumentParser().parse_args()
    documents, links = collect_artifacts()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        docs_tmp = tmp / "documents.jsonl"
        links_tmp = tmp / "links.jsonl"
        write_jsonl(docs_tmp, documents)
        write_jsonl(links_tmp, links)
        current_docs = read_lines(ROOT / "index" / "documents.jsonl")
        current_links = read_lines(ROOT / "index" / "links.jsonl")
        expected_docs = read_lines(docs_tmp)
        expected_links = read_lines(links_tmp)
    failures = []
    if current_docs != expected_docs:
        failures.append({"target": "documents.jsonl", "current_lines": len(current_docs), "expected_lines": len(expected_docs)})
    if current_links != expected_links:
        failures.append({"target": "links.jsonl", "current_lines": len(current_links), "expected_lines": len(expected_links)})
    payload = {"ok": not failures, "check": "check_index_consistency", "summary": "index files match rebuild output" if not failures else "index files differ from rebuild output", "failures": failures}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''


CHECK_HELPER_SCRIPT = r'''from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SUPPORT_RANK = {
    "derived_summary": 1,
    "extract": 2,
    "raw_source": 3,
}


def load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PyYAML is required for recipe-backed checks. Re-run with `uv run python scripts/run_archive_check.py ...`."
        ) from exc
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_json_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def emit(payload: dict) -> int:
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if payload.get("ok") else 1


def iter_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def tokenize(text: str) -> list[str]:
    token = []
    tokens = []
    for ch in text.lower():
        if ch.isalnum():
            token.append(ch)
        elif token:
            tokens.append("".join(token))
            token = []
    if token:
        tokens.append("".join(token))
    return tokens


def labels_for_entry(entry: dict) -> list[str]:
    labels = []
    for key in ("topic", "label"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            labels.append(value.strip())
    for key in ("labels", "match_terms", "artifact_ids"):
        value = entry.get(key)
        if isinstance(value, list):
            labels.extend(str(item).strip() for item in value if str(item).strip())
    return labels


def entry_matches_term(entry: dict, term: str) -> bool:
    if not term.strip():
        return False
    lowered_term = term.lower()
    term_tokens = set(tokenize(term))
    for label in labels_for_entry(entry):
        lowered_label = label.lower()
        if lowered_term in lowered_label or lowered_label in lowered_term:
            return True
        label_tokens = set(tokenize(label))
        if term_tokens and label_tokens and term_tokens <= label_tokens:
            return True
        if term_tokens and label_tokens and len(term_tokens & label_tokens) >= min(2, len(term_tokens)):
            return True
    return False


def infer_support_kind(claim: dict, documents_by_id: dict[str, dict]) -> str | None:
    support_kind = claim.get("support_kind") or claim.get("support_type")
    if support_kind:
        return str(support_kind)
    evidence_ids = claim.get("evidence_ids", [])
    inferred = []
    for artifact_id in evidence_ids:
        artifact = documents_by_id.get(artifact_id, {})
        artifact_type = artifact.get("artifact_type")
        if artifact_type == "extract":
            inferred.append("extract")
        elif artifact_type in {"raw_source", "source_document"}:
            inferred.append("raw_source")
        elif artifact_type:
            inferred.append("derived_summary")
    if "raw_source" in inferred:
        return "raw_source"
    if "extract" in inferred:
        return "extract"
    if "derived_summary" in inferred:
        return "derived_summary"
    return None


def write_temp_payload(payload_text: str, prefix: str) -> str:
    data = json.loads(payload_text)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", prefix=prefix, delete=False)
    with handle as fh:
        json.dump(data, fh, ensure_ascii=True, indent=2)
        fh.write("\n")
    return handle.name


def run_subprocess(cmd: list[str]) -> int:
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if stdout:
        print(stdout)
    elif stderr:
        print(json.dumps({
            "ok": False,
            "summary": "underlying check failed",
            "failures": [{"reason": stderr}],
        }, ensure_ascii=True, indent=2))
    return completed.returncode


def validate_support_hierarchy(root: Path, claims_path: Path) -> int:
    try:
        config = load_yaml(root / "recipes" / "support-hierarchy.yaml")
    except RuntimeError as exc:
        return emit({"ok": False, "summary": "support hierarchy check unavailable", "failures": [{"reason": str(exc)}]})
    payload = load_json_file(claims_path)
    failures = []
    checked = 0
    documents_by_id = {row.get("artifact_id"): row for row in iter_jsonl(root / "index" / "documents.jsonl")}
    minimum = config.get("decisive_claim_minimum", "extract")
    minimum_rank = SUPPORT_RANK.get(minimum, 2)
    require_label = bool(config.get("require_support_label_per_decisive_claim", True))
    for claim in payload.get("claims", []):
        if not claim.get("decisive"):
            continue
        checked += 1
        support_type = infer_support_kind(claim, documents_by_id)
        if require_label and not support_type:
            failures.append({"claim_id": claim.get("claim_id"), "reason": "missing support_type"})
            continue
        if support_type not in SUPPORT_RANK:
            failures.append({"claim_id": claim.get("claim_id"), "reason": f"unknown support_type: {support_type}"})
            continue
        if SUPPORT_RANK[support_type] < minimum_rank:
            failures.append({"claim_id": claim.get("claim_id"), "reason": f"decisive claim requires at least {minimum}", "support_type": support_type})
    if payload.get("claims") and checked == 0:
        failures.append({"reason": "no decisive claims were supplied"})
    return emit({
        "ok": not failures,
        "check": "check_support_hierarchy",
        "summary": "decisive claims meet support hierarchy" if not failures else "decisive claims blocked by support hierarchy",
        "counts": {"claims_checked": checked, "failures": len(failures)},
        "failures": failures,
    })


def validate_coverage_state(root: Path, term: str | None, task_type: str | None) -> int:
    try:
        coverage = load_yaml(root / "domain" / "coverage-ledger.yaml")
        answer_contract = load_yaml(root / "recipes" / "answer-contract.yaml")
    except RuntimeError as exc:
        return emit({"ok": False, "summary": "coverage-state check unavailable", "failures": [{"reason": str(exc)}]})
    normalized_term = (term or "").strip()
    matched_provisional = []
    for entry in coverage.get("provisional_weak_slices", []):
        if not isinstance(entry, dict):
            continue
        task_types = entry.get("task_types")
        if isinstance(task_types, list) and task_type and task_type not in {str(item) for item in task_types}:
            continue
        if entry_matches_term(entry, normalized_term):
            matched_provisional.append(entry)
    matched_partial = []
    for entry in coverage.get("partial_topics", []):
        if isinstance(entry, dict) and entry_matches_term(entry, normalized_term):
            matched_partial.append(entry)
    matched_gaps = []
    for entry in coverage.get("support_gaps", []):
        if not isinstance(entry, dict):
            continue
        task_types = entry.get("task_types")
        if isinstance(task_types, list) and task_type and task_type not in {str(item) for item in task_types}:
            continue
        if entry_matches_term(entry, normalized_term):
            matched_gaps.append(entry)
    support_targets = answer_contract.get("support_targets", {}) if isinstance(answer_contract, dict) else {}
    support_target = support_targets.get(task_type or "", support_targets.get("rule_lookup"))
    if matched_provisional or matched_partial or matched_gaps:
        failures = []
        status = "known_below_target"
        summary = "coverage ledger marks this topic below target quality"
        if matched_provisional and not matched_partial and not matched_gaps:
            status = "likely_below_target"
            summary = "coverage ledger records a provisional weak slice for this topic"
            failures.append({"reason": "matched provisional weak slice", "provisional_weak_slices": matched_provisional})
        elif matched_provisional:
            failures.append({"reason": "matched provisional weak slice", "provisional_weak_slices": matched_provisional})
        if matched_partial:
            failures.append({"reason": "matched partial topic", "topics": matched_partial})
        if matched_gaps:
            failures.append({"reason": "matched support gap", "gaps": matched_gaps})
        return emit({
            "ok": False,
            "check": "check_coverage_state",
            "summary": summary,
            "status": status,
            "counts": {
                "matched_provisional_weak_slices": len(matched_provisional),
                "matched_partial_topics": len(matched_partial),
                "matched_support_gaps": len(matched_gaps),
            },
            "support_target": support_target,
            "suggested_action": "expand",
            "can_answer_provisionally": True,
            "failures": failures,
        })
    return emit({
        "ok": True,
        "check": "check_coverage_state",
        "summary": "no matching partial topic or support gap in coverage ledger",
        "status": "clear",
        "counts": {
            "matched_provisional_weak_slices": 0,
            "matched_partial_topics": 0,
            "matched_support_gaps": 0,
        },
        "support_target": support_target,
        "failures": [],
    })


def validate_auto_expand_decision(root: Path, term: str | None, task_type: str | None, decision_path: Path) -> int:
    try:
        answer_contract = load_yaml(root / "recipes" / "answer-contract.yaml")
    except RuntimeError as exc:
        return emit({"ok": False, "summary": "auto-expand decision check unavailable", "failures": [{"reason": str(exc)}]})
    if not bool(answer_contract.get("auto_expand_when_below_target", False)):
        return emit({
            "ok": True,
            "check": "check_auto_expand_decision",
            "summary": "auto-expand policy disabled for this pack",
            "failures": [],
        })
    coverage = load_yaml(root / "domain" / "coverage-ledger.yaml")
    decision = load_json_file(decision_path)
    normalized_term = (term or "").strip()
    matched_provisional = []
    for entry in coverage.get("provisional_weak_slices", []):
        if not isinstance(entry, dict):
            continue
        task_types = entry.get("task_types")
        if isinstance(task_types, list) and task_type and task_type not in {str(item) for item in task_types}:
            continue
        if entry_matches_term(entry, normalized_term):
            matched_provisional.append(entry)
    matched_gaps = []
    for entry in coverage.get("support_gaps", []):
        if not isinstance(entry, dict):
            continue
        task_types = entry.get("task_types")
        if isinstance(task_types, list) and task_type and task_type not in {str(item) for item in task_types}:
            continue
        if entry_matches_term(entry, normalized_term):
            matched_gaps.append(entry)
    matched_partial = []
    for entry in coverage.get("partial_topics", []):
        if isinstance(entry, dict) and entry_matches_term(entry, normalized_term):
            matched_partial.append(entry)
    if not matched_provisional and not matched_gaps and not matched_partial:
        return emit({
            "ok": True,
            "check": "check_auto_expand_decision",
            "summary": "no below-target coverage state matched for this term",
            "failures": [],
        })
    allowed_non_expand = {
        str(item) for item in answer_contract.get("allow_non_expand_actions_when_below_target", [])
    }
    action = str(decision.get("action", "")).lower()
    scope_status = str(decision.get("scope_status", "")).lower()
    if action == "expand":
        return emit({
            "ok": True,
            "check": "check_auto_expand_decision",
            "summary": "decision respects auto-expand policy for below-target coverage",
            "counts": {
                "matched_provisional_weak_slices": len(matched_provisional),
                "matched_partial_topics": len(matched_partial),
                "matched_support_gaps": len(matched_gaps),
            },
            "failures": [],
        })
    if action in allowed_non_expand and scope_status == "insufficient_input":
        return emit({
            "ok": True,
            "check": "check_auto_expand_decision",
            "summary": "non-expand action allowed because the blocker is insufficient input",
            "counts": {
                "matched_provisional_weak_slices": len(matched_provisional),
                "matched_partial_topics": len(matched_partial),
                "matched_support_gaps": len(matched_gaps),
            },
            "failures": [],
        })
    return emit({
        "ok": False,
        "check": "check_auto_expand_decision",
        "summary": "decision violates auto-expand policy for below-target coverage",
        "counts": {
            "matched_provisional_weak_slices": len(matched_provisional),
            "matched_partial_topics": len(matched_partial),
            "matched_support_gaps": len(matched_gaps),
        },
        "failures": [
            {
                "reason": "below-target coverage requires expand by default",
                "term": normalized_term,
                "task_type": task_type,
                "actual_action": action,
                "allowed_non_expand_actions": sorted(allowed_non_expand),
            }
        ],
    })


def validate_confirmation_boundary(root: Path, answer_path: Path) -> int:
    try:
        config = load_yaml(root / "recipes" / "confirmation-thresholds.yaml")
    except RuntimeError as exc:
        return emit({"ok": False, "summary": "confirmation boundary check unavailable", "failures": [{"reason": str(exc)}]})
    payload = load_json_file(answer_path)
    failures = []
    level = payload.get("conclusion_level")
    allowed = set(config.get("allowed_conclusion_levels", []))
    if level not in allowed:
        failures.append({"field": "conclusion_level", "reason": f"not allowed: {level}"})
    blocking_fact_ids = set(config.get("blocking_fact_ids", []))
    confirmed = set(payload.get("blocking_facts_confirmed", []))
    missing = set(payload.get("blocking_facts_missing", []))
    phrasing = str(payload.get("phrasing", "")).lower()
    unresolved = blocking_fact_ids - confirmed
    if missing & confirmed:
        failures.append({"field": "blocking_facts", "reason": "same blocking fact marked confirmed and missing"})
    if level == "confirmed_from_provided_facts" and config.get("confirmed_requires_all_blocking_facts", True) and unresolved:
        failures.append({"field": "conclusion_level", "reason": "confirmed conclusion requires all blocking facts confirmed", "unresolved_blocking_facts": sorted(unresolved)})
    for phrase in [p.lower() for p in config.get("forbidden_phrases_when_blocking_facts_missing", [])]:
        if unresolved and phrase in phrasing:
            failures.append({"field": "phrasing", "reason": "forbidden phrase used while blocking facts remain unresolved", "phrase": phrase})
    return emit({
        "ok": not failures,
        "check": "check_confirmation_boundary",
        "summary": "answer stays within confirmation boundary" if not failures else "answer overclaims beyond confirmation boundary",
        "counts": {
            "blocking_facts_configured": len(blocking_fact_ids),
            "blocking_facts_confirmed": len(confirmed),
            "blocking_facts_missing": len(missing),
            "failures": len(failures),
        },
        "failures": failures,
    })


def validate_currentness(root: Path, currentness_path: Path) -> int:
    try:
        config = load_yaml(root / "recipes" / "currentness-rules.yaml")
    except RuntimeError as exc:
        return emit({"ok": False, "summary": "currentness check unavailable", "failures": [{"reason": str(exc)}]})
    payload = load_json_file(currentness_path)
    failures = []
    question_shape = payload.get("question_shape")
    status = payload.get("status")
    reason = str(payload.get("reason", "")).strip()
    allowed_statuses = set(config.get("allowed_statuses", []))
    required_fields = ["status", *config.get("proof_bundle_fields", [])]
    for field in required_fields:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            failures.append({"field": field, "reason": "missing required field"})
    current_shapes = set(config.get("current_question_shapes", []))
    if question_shape and current_shapes and question_shape not in current_shapes:
        failures.append({"field": "question_shape", "reason": f"not enabled for currentness: {question_shape}"})
    if status and status not in allowed_statuses:
        failures.append({"field": "status", "reason": f"not allowed: {status}"})
    blocking_status = config.get("block_decisive_current_answers_unless_status", "current")
    if status and status != blocking_status:
        failures.append({"field": "status", "reason": f"current-state answer blocked while status is {status}"})
    if status in {"stale", "superseded", "unproven"} and not reason:
        failures.append({"field": "reason", "reason": f"{status} status requires an explanation"})
    return emit({
        "ok": not failures,
        "check": "check_currentness",
        "summary": "currentness proof accepted" if not failures else "currentness proof blocked",
        "status": status,
        "question_shape": question_shape,
        "counts": {"failures": len(failures)},
        "failures": failures,
    })


def validate_expansion_plan(root: Path, plan_path: Path) -> int:
    plan = load_json_file(plan_path)
    try:
        source_families = load_yaml(root / "recipes" / "source-families.yaml")
        acquisition = load_yaml(root / "recipes" / "source-acquisition.yaml")
        extract_units = load_yaml(root / "recipes" / "extract-units.yaml")
        answer_contract = load_yaml(root / "recipes" / "answer-contract.yaml")
    except RuntimeError as exc:
        return emit({"ok": False, "summary": "expansion plan check unavailable", "failures": [{"reason": str(exc)}]})
    failures = []
    required = {"task_type", "source_family", "source_url", "unit_type", "materialize_as", "persistence_action", "reason"}
    for key in sorted(required - set(plan)):
        failures.append({"field": key, "reason": "missing required field"})
    allowed_families = {row.get("name") for row in source_families.get("source_families", []) if isinstance(row, dict) and row.get("name")}
    source_family = plan.get("source_family")
    if source_family and source_family not in allowed_families:
        failures.append({"field": "source_family", "reason": f"not allowed: {source_family}"})
    if source_family and source_family not in set(acquisition.get("allowed_source_families", [])):
        failures.append({"field": "source_family", "reason": "not present in source-acquisition recipe"})
    unit_map = {row.get("source_family"): row for row in extract_units.get("units", []) if isinstance(row, dict) and row.get("source_family")}
    unit_config = unit_map.get(source_family, {})
    if plan.get("unit_type") and unit_config.get("retrieval_unit") and plan["unit_type"] != unit_config["retrieval_unit"]:
        failures.append({"field": "unit_type", "reason": f"expected {unit_config['retrieval_unit']} for source_family {source_family}"})
    if plan.get("materialize_as") and unit_config.get("materialize_as") and plan["materialize_as"] != unit_config["materialize_as"]:
        failures.append({"field": "materialize_as", "reason": f"expected {unit_config['materialize_as']} for source_family {source_family}"})
    if answer_contract.get("exact_wording") in {"important", "critical"} and plan.get("exact_wording_claim") and plan.get("materialize_as") != "extract":
        failures.append({"field": "materialize_as", "reason": "exact wording claims require extract materialization under this domain pack"})
    if plan.get("task_type") == "case_application" and not plan.get("facts_status"):
        failures.append({"field": "facts_status", "reason": "required for case_application"})
    if plan.get("persistence_action") not in {"persist", "skip_persist"}:
        failures.append({"field": "persistence_action", "reason": "must be persist or skip_persist"})
    if plan.get("persistence_action") == "skip_persist":
        skip_reason = plan.get("skip_reason")
        if not skip_reason:
            failures.append({"field": "skip_reason", "reason": "required when persistence_action is skip_persist"})
        elif skip_reason not in set(acquisition.get("skip_persist_reasons", [])):
            failures.append({"field": "skip_reason", "reason": f"not allowed: {skip_reason}"})
    return emit({
        "ok": not failures,
        "check": "check_expansion_plan",
        "summary": "expansion plan accepted" if not failures else "expansion plan blocked",
        "counts": {"failures": len(failures)},
        "failures": failures,
    })


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=[
        "check_coverage",
        "check_coverage_state",
        "check_auto_expand_decision",
        "check_provenance",
        "check_policy",
        "check_decision_record",
        "check_claim_support",
        "check_exact_wording",
        "check_support_hierarchy",
        "check_confirmation_boundary",
        "check_currentness",
        "check_expansion_plan",
        "rebuild_index",
    ])
    parser.add_argument("--archive-root", default=".")
    parser.add_argument("--term")
    parser.add_argument("--action", default="answer")
    parser.add_argument("--autonomy-policy", default="proactive")
    parser.add_argument("--task-type")
    parser.add_argument("--claims-json")
    parser.add_argument("--decision-json")
    parser.add_argument("--plan-json")
    parser.add_argument("--answer-json")
    parser.add_argument("--claims-payload")
    parser.add_argument("--decision-payload")
    parser.add_argument("--plan-payload")
    parser.add_argument("--answer-payload")
    parser.add_argument("--currentness-json")
    parser.add_argument("--currentness-payload")
    return parser


def require_payload_path_or_inline(path_value: str | None, inline_value: str | None, field_name: str) -> tuple[str | None, dict | None]:
    if path_value:
        return path_value, None
    if inline_value:
        try:
            return write_temp_payload(inline_value, f"{field_name}-"), None
        except json.JSONDecodeError as exc:
            return None, {
                "ok": False,
                "summary": f"invalid inline JSON for {field_name}",
                "failures": [{"reason": str(exc)}],
                "suggestions": [
                    f"Pass a file path with --{field_name}-json or valid inline JSON with --{field_name}-payload.",
                ],
            }
    return None, {
        "ok": False,
        "summary": f"missing {field_name} payload",
        "failures": [{"reason": f"provide --{field_name}-json or --{field_name}-payload"}],
        "suggestions": [
            f"Use --{field_name}-payload '{{...}}' for inline JSON.",
            f"Or write a file and pass --{field_name}-json /path/to/{field_name}.json.",
        ],
    }


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    root = Path(args.archive_root).resolve()
    verifier = root / "scripts" / "archive_verifier.py"
    temp_paths: list[str] = []
    try:
        if args.command in {"check_coverage", "check_provenance", "check_policy", "rebuild_index"}:
            cmd = [sys.executable, str(verifier), args.command, str(root)]
            if args.command == "check_coverage" and args.term:
                cmd += ["--term", args.term]
            if args.command == "check_policy":
                cmd += ["--action", args.action, "--autonomy-policy", args.autonomy_policy]
            return run_subprocess(cmd)
        if args.command == "check_coverage_state":
            return validate_coverage_state(root, args.term, args.task_type)
        if args.command == "check_auto_expand_decision":
            decision_path, error = require_payload_path_or_inline(args.decision_json, args.decision_payload, "decision")
            if error:
                return emit(error)
            assert decision_path is not None
            if args.decision_payload:
                temp_paths.append(decision_path)
            return validate_auto_expand_decision(root, args.term, args.task_type, Path(decision_path))
        if args.command in {"check_claim_support", "check_exact_wording"}:
            claims_path, error = require_payload_path_or_inline(args.claims_json, args.claims_payload, "claims")
            if error:
                return emit(error)
            assert claims_path is not None
            if args.claims_payload:
                temp_paths.append(claims_path)
            cmd = [sys.executable, str(verifier), args.command, str(root), "--claims-json", claims_path]
            return run_subprocess(cmd)
        if args.command == "check_decision_record":
            decision_path, error = require_payload_path_or_inline(args.decision_json, args.decision_payload, "decision")
            if error:
                return emit(error)
            assert decision_path is not None
            if args.decision_payload:
                temp_paths.append(decision_path)
            cmd = [sys.executable, str(verifier), args.command, str(root), "--decision-json", decision_path]
            return run_subprocess(cmd)
        if args.command == "check_support_hierarchy":
            claims_path, error = require_payload_path_or_inline(args.claims_json, args.claims_payload, "claims")
            if error:
                return emit(error)
            assert claims_path is not None
            if args.claims_payload:
                temp_paths.append(claims_path)
            return validate_support_hierarchy(root, Path(claims_path))
        if args.command == "check_confirmation_boundary":
            answer_path, error = require_payload_path_or_inline(args.answer_json, args.answer_payload, "answer")
            if error:
                return emit(error)
            assert answer_path is not None
            if args.answer_payload:
                temp_paths.append(answer_path)
            return validate_confirmation_boundary(root, Path(answer_path))
        if args.command == "check_currentness":
            currentness_path, error = require_payload_path_or_inline(
                args.currentness_json, args.currentness_payload, "currentness"
            )
            if error:
                return emit(error)
            assert currentness_path is not None
            if args.currentness_payload:
                temp_paths.append(currentness_path)
            return validate_currentness(root, Path(currentness_path))
        if args.command == "check_expansion_plan":
            plan_path, error = require_payload_path_or_inline(args.plan_json, args.plan_payload, "plan")
            if error:
                return emit(error)
            assert plan_path is not None
            if args.plan_payload:
                temp_paths.append(plan_path)
            return validate_expansion_plan(root, Path(plan_path))
        return emit({"ok": False, "summary": "unsupported command", "failures": [{"reason": args.command}]})
    finally:
        for path in temp_paths:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
'''


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def scaffold(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for relative in (
        "source/downloads",
        "source/manifests",
        "source/extracted",
        "artifacts/registry",
        "artifacts/extracts",
        "artifacts/derived",
        "config",
        "sql",
        "docs",
        "scripts",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)
    _write(root / "README.md", README)
    _write(root / "config/index-policy.yaml", INDEX_POLICY)
    _write(root / "sql/schema.sql", SCHEMA)
    _write(root / "docs/promotion-rules.md", PROMOTION_RULES)
    _write(root / "scripts/archive_verifier.py", VERIFIER_SCRIPT)
    _write(root / "scripts/rebuild_index.py", REBUILD_SCRIPT)
    _write(root / "scripts/check_index_consistency.py", CONSISTENCY_SCRIPT)
    _write(root / "scripts/run_archive_check.py", CHECK_HELPER_SCRIPT)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: scaffold_archive_index.py OUTPUT_DIR", file=sys.stderr)
        return 2
    scaffold(Path(argv[1]).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
