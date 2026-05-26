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
  allowed_source_types:
    - official
    - unofficial
  allowed_scope_statuses:
    - in_bounds
    - out_of_bounds
  allowed_artifact_kinds:
    - canonical
    - reusable
    - ad_hoc
    - extract
    - derived_summary
    - crosswalk
    - resolution
    - calculation
    - temporary_case_note
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
        if not line.strip():
            continue
        if line.startswith("  "):
            continue
        if line.startswith("- ") and current_key:
            data.setdefault(current_key, [])
            data[current_key].append(line[2:].strip())
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


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: scaffold_archive_index.py OUTPUT_DIR", file=sys.stderr)
        return 2
    scaffold(Path(argv[1]).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
