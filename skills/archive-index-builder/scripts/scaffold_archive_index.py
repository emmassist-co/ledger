from __future__ import annotations

import sys
from pathlib import Path


README = """# Archive Index Workspace

This workspace is a cheap-first retrieval scaffold for large archives.

Start with:

- `AGENTS.md`
- `config/index-policy.yaml`
- `sql/schema.sql`
- `docs/promotion-rules.md`
- `scripts/archive_verifier.py`
- `scripts/rebuild_index.py`
- `scripts/check_index_consistency.py`
- `AUDIT_AGENT.md`
- `TESTING.md`

After the archive is usable, validate it with the separate `archive-evals` companion skill.

Build in layers:

- `source/downloads/`: saved canonical source files
- `source/manifests/`: acquisition metadata and hashes
- `source/index/`: generated source-side retrieval indexes such as PDF pages or website sections
- `artifacts/registry/`: one entry per source document
- `artifacts/extracts/`: verbatim or deterministic extract units
- `artifacts/derived/`: summaries, crosswalks, claims, entities, resolutions

Do not let LLM-authored artifacts become the only surviving representation of source text.
Do not hand-edit derived index outputs. Rebuild them from source artifacts.

Acquisition order for public websites and PDFs:

1. prefer canonical official downloads when they exist
2. otherwise capture public pages as clean Markdown
3. for PDFs, run page-level extraction and indexing before reading the full file
4. build local page or section indexes over the captured text
5. search those local indexes before opening large sources end to end
6. escalate to a browser only when rendering or interaction is truly required

PDF default:

- preserve the raw PDF under `source/downloads/`
- extract with `liteparse`
- persist both extracted Markdown and structured JSON under `source/extracted/`
- build searchable page indexes under `source/index/`
- prefer `uv run ledger archive search-pdf ...` style page retrieval over full-document rereads

Do not use full PDF rereads as the normal model-facing path when page-level retrieval is available.
Do not use raw HTML, bundled JavaScript, or page chrome as the default model-facing retrieval surface.

Generic operator defaults:

- classify work as `rule_lookup` or `case_application`
- treat `not indexed yet` as a signal to measure coverage, not as a final answer
- use deterministic scripts as gates, not as a replacement for operator reasoning
- when subagents are available, delegate isolated discovery, fetch, indexing, or verification tasks that can run independently
- require a compact decision record before `expand`, `persist`, or `skip_persist`
- block exact wording unless support is `raw_source` or `extract`
- prefer reusable extract artifacts over mixed ad hoc notes
"""


AGENTS = """# Archive Agent Guide

This is a live archive workspace. Treat it as an evidence router with local persistence, not as a scratch crawler.

## Default Loop

1. Query the local archive first.
2. Classify the request as `rule_lookup` or `case_application`.
3. Check whether archive coverage is actually sufficient before treating a found artifact as decisive.
4. Prefer canonical official sources for missing in-bounds slices.
5. For public web pages, prefer clean Markdown capture before any browser step.
6. Build and use local page or section indexes before reading large sources end to end.
7. Persist reusable canonical material back into the archive before finalizing answers.
8. Use broader web search or browser automation only when the local archive, canonical path, and clean capture path are insufficient.
9. When subagents are available, spawn them for bounded archive tasks that can be isolated cleanly, but keep final synthesis and persistence decisions in the main thread.

## Web And PDF Acquisition Order

1. canonical official document download when available
2. Markdown-first public capture such as `uv run ledger archive fetch-url --root <archive-root> --source-id <id> --url <public-url>`
3. for PDFs, extract and index pages before reading the whole file
4. local page or section index search over captured Markdown or extracted PDF pages
5. agent browser only when the page genuinely requires rendering or interaction

## PDF Rule

- preserve the raw PDF locally
- extract pages with `liteparse`
- persist extracted Markdown plus structured JSON
- use page-level search and retrieval before opening the whole PDF
- only reread the full PDF when the page index is insufficient

## Coverage Rule

- treat `not indexed yet` as a coverage question first, not as a final answer
- when support may be partial, run a deterministic coverage check before making decisive claims
- if a weak slice is discovered during expansion, record that suspicion so later operators can revisit it instead of rediscovering it from scratch

## Decision Rule

- before `expand`, `persist`, or `skip_persist`, write a compact structured decision record
- include at least `action`, `reason`, `source_type`, `scope_status`, and `artifact_kind`
- if skipping persistence, include an explicit skip reason

## Support Rule

- treat exact wording as a higher bar than paraphrase
- block exact wording unless support is `raw_source` or `extract`
- label decisive claims with their actual support strength instead of implying stronger support than exists

## Persistence Rule

- new reusable verbatim or near-verbatim source material should land in `artifacts/extracts/`
- prefer durable reusable extracts over mixed one-off notes
- treat legacy mixed note areas as read paths unless the archive explicitly says otherwise

## Testing Rule

- deterministic checks are necessary but not sufficient
- for meaningful archive behavior changes, require at least one independent agent-style run against a real in-bounds question
- use scripts as deterministic gates, not as the whole operating workflow
- when subagents are available, use them for parallel bounded checks or source-family investigations rather than serializing everything in one thread

Raw HTML, JavaScript bundles, menus, and footer chrome are audit artifacts, not the default model-facing retrieval surface.
"""


AUDIT_GUIDE = """# Agent Audit

Use this file to review whether an agent used the archive correctly, not just whether the final answer sounded plausible.

## What Good Looks Like

The agent should:

- read `AGENTS.md` first
- classify the task as `rule_lookup` or `case_application`
- query the archive before external search
- measure coverage before treating a found artifact as decisive when the topic may be partial
- use deterministic scripts as gates instead of scripting the whole workflow
- prefer canonical expansion for in-bounds gaps
- use clean Markdown capture and local indexes before browser escalation
- when subagents are available, use them for isolated fetch / verification / source-family subtasks
- write a decision record before `expand`, `persist`, or `skip_persist`
- block exact wording unless support is `raw_source` or `extract`
- persist reusable canonical material instead of one-off case notes

## Red Flags

- the agent answered directly from a found artifact without checking likely coverage gaps
- the agent said `not indexed yet` where in-bounds expansion was available
- the agent used raw HTML or full-PDF rereads where a clean indexed path was available
- the agent escalated to a browser before trying cheaper clean capture and local retrieval
- the agent persisted or skipped persistence without a decision record
- the answer posture overstated the actual support strength
"""


TESTING = """# Testing

This file is for testing a live archive workspace.

## Core Rule

Deterministic script passes are necessary but not sufficient.

When you change archive operation, enrichment behavior, persistence behavior, or answer posture, testing is not complete until another agent can operate the archive correctly on a real in-bounds question.

## Pass Criteria

The independent run passes only if the other agent:

1. Starts from the local archive and `AGENTS.md`.
2. Classifies the work as `rule_lookup` or `case_application`.
3. Uses deterministic scripts as gates rather than as the whole workflow.
4. Checks coverage before making decisive claims on potentially partial topics.
5. Expands through canonical sources when local support is weak and the topic is in-bounds.
6. Uses clean capture and local indexed retrieval before escalating to a browser.
7. Uses available subagents for bounded parallel work when that reduces serial archive slog.
8. Persists reusable material in the explicit extract layer.
9. Respects exact-wording and support-strength rules.
10. Returns an answer whose posture matches the support actually available.
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
from datetime import date
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


def dump_yaml(path: Path, payload: object) -> None:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PyYAML is required for recipe-backed checks. Re-run with `uv run python scripts/run_archive_check.py ...`."
        ) from exc
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding="utf-8")


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


def documents_by_id(root: Path) -> dict[str, dict]:
    return {row.get("artifact_id"): row for row in iter_jsonl(root / "index" / "documents.jsonl")}


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


def register_provisional_weak_slice(root: Path, term: str | None, task_type: str | None, decision_path: Path) -> int:
    normalized_term = (term or "").strip()
    if not normalized_term:
        return emit({
            "ok": False,
            "check": "register_provisional_weak_slice",
            "summary": "term is required to register provisional weak slice",
            "failures": [{"reason": "provide --term"}],
        })
    coverage = load_coverage_ledger(root)
    if matching_support_gap_entries(coverage, normalized_term, task_type):
        return emit({
            "ok": True,
            "check": "register_provisional_weak_slice",
            "summary": "matching support gap already exists; provisional registration skipped",
            "status": "existing_confirmed_gap",
            "counts": {"created": 0},
            "failures": [],
        })
    if matching_provisional_entries(coverage, normalized_term, task_type):
        return emit({
            "ok": True,
            "check": "register_provisional_weak_slice",
            "summary": "matching provisional weak slice already exists",
            "status": "existing_provisional",
            "counts": {"created": 0},
            "failures": [],
        })

    decision = load_json_file(decision_path)
    action = str(decision.get("action", "")).lower()
    if action != "expand":
        return emit({
            "ok": False,
            "check": "register_provisional_weak_slice",
            "summary": "only expand decisions can register provisional weak slices",
            "failures": [{"reason": f"decision action must be expand, got {action or 'missing'}"}],
        })

    quality_status = str(decision.get("quality_status", "")).lower()
    if quality_status and quality_status not in {"provisional", "below_target"}:
        return emit({
            "ok": False,
            "check": "register_provisional_weak_slice",
            "summary": "decision quality status does not justify provisional registration",
            "failures": [{"reason": f"unsupported quality_status: {quality_status}"}],
        })

    artifact_ids = [str(item).strip() for item in decision.get("artifact_ids", []) if str(item).strip()]
    current_support = str(decision.get("current_support", "")).strip() or infer_current_support(root, artifact_ids)
    source_family = str(decision.get("source_family", "")).strip()
    reason = str(decision.get("reason", "")).strip()
    if not reason:
        return emit({
            "ok": False,
            "check": "register_provisional_weak_slice",
            "summary": "decision reason is required for provisional registration",
            "failures": [{"reason": "decision reason missing"}],
        })

    labels = [normalized_term]
    for item in decision.get("match_terms", []):
        label = str(item).strip()
        if label and label not in labels:
            labels.append(label)
    notes = [
        f"Registered automatically from expand decision on {date.today().isoformat()}.",
        "This provisional slice should be confirmed, cleared, or superseded after later enrichment.",
    ]
    for item in decision.get("notes", []):
        note = str(item).strip()
        if note and note not in notes:
            notes.append(note)
    entry = {
        "topic": str(decision.get("topic", "")).strip() or slugify_term(normalized_term),
        "labels": labels,
        "task_types": [task_type] if task_type else [],
        "suspected_support_gap": str(decision.get("suspected_support_gap", "")).strip() or "suspected_weak_slice",
        "current_support": current_support or "unknown",
        "reason": reason,
        "source_family": source_family or "unknown",
        "artifact_ids": artifact_ids,
        "notes": notes,
    }
    coverage.setdefault("provisional_weak_slices", []).append(entry)
    save_coverage_ledger(root, coverage)
    return emit({
        "ok": True,
        "check": "register_provisional_weak_slice",
        "summary": "provisional weak slice registered",
        "status": "created",
        "counts": {"created": 1},
        "entry": entry,
        "failures": [],
    })


def resolve_provisional_weak_slice(
    root: Path,
    term: str | None,
    task_type: str | None,
    resolution: str | None,
    resolution_path: Path | None,
) -> int:
    normalized_term = (term or "").strip()
    outcome = str(resolution or "").strip().lower()
    if not normalized_term:
        return emit({
            "ok": False,
            "check": "resolve_provisional_weak_slice",
            "summary": "term is required to resolve provisional weak slice",
            "failures": [{"reason": "provide --term"}],
        })
    if outcome not in {"confirmed", "cleared", "superseded"}:
        return emit({
            "ok": False,
            "check": "resolve_provisional_weak_slice",
            "summary": "resolution must be confirmed, cleared, or superseded",
            "failures": [{"reason": f"unsupported resolution: {resolution}"}],
        })

    coverage = load_coverage_ledger(root)
    matched = matching_provisional_entries(coverage, normalized_term, task_type)
    if not matched:
        return emit({
            "ok": False,
            "check": "resolve_provisional_weak_slice",
            "summary": "no matching provisional weak slice found",
            "failures": [{"reason": "no matching provisional weak slice"}],
        })

    resolution_payload = load_json_file(resolution_path) if resolution_path else {}
    target = matched[0]
    coverage["provisional_weak_slices"] = [
        entry for entry in coverage.get("provisional_weak_slices", []) if entry is not target
    ]
    note = str(resolution_payload.get("note", "")).strip()
    dated_note = f"{outcome.title()} provisional weak slice `{target.get('topic', normalized_term)}` on {date.today().isoformat()}."
    if note:
        dated_note = f"{dated_note} {note}"

    if outcome == "confirmed":
        answer_contract = load_yaml(root / "recipes" / "answer-contract.yaml")
        support_targets = answer_contract.get("support_targets", {}) if isinstance(answer_contract, dict) else {}
        required_support = (
            str(resolution_payload.get("required_support", "")).strip()
            or support_targets.get(task_type or "", support_targets.get("rule_lookup"))
            or "extract"
        )
        support_gap = {
            "topic": target.get("topic"),
            "labels": target.get("labels", []),
            "task_types": target.get("task_types", [task_type] if task_type else []),
            "required_support": required_support,
            "current_support": resolution_payload.get("current_support") or target.get("current_support", "unknown"),
            "quality_status": "below_target",
            "follow_up_action": str(resolution_payload.get("follow_up_action", "")).strip() or "expand",
            "source_family": target.get("source_family", "unknown"),
            "artifact_ids": target.get("artifact_ids", []),
            "notes": list(target.get("notes", [])) + [dated_note],
        }
        coverage.setdefault("support_gaps", []).append(support_gap)
        save_coverage_ledger(root, coverage)
        return emit({
            "ok": True,
            "check": "resolve_provisional_weak_slice",
            "summary": "provisional weak slice confirmed and promoted to support gap",
            "status": "confirmed",
            "counts": {"resolved": 1},
            "entry": support_gap,
            "failures": [],
        })

    append_coverage_note(coverage, dated_note)
    save_coverage_ledger(root, coverage)
    return emit({
        "ok": True,
        "check": "resolve_provisional_weak_slice",
        "summary": f"provisional weak slice {outcome}",
        "status": outcome,
        "counts": {"resolved": 1},
        "failures": [],
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
    required = {"task_type", "question_shape", "source_family", "source_url", "unit_type", "materialize_as", "persistence_action", "search_stage", "query_terms", "reason"}
    for key in sorted(required - set(plan)):
        failures.append({"field": key, "reason": "missing required field"})
    question_shape_policies = {
        row.get("name"): row
        for row in acquisition.get("question_shape_policies", [])
        if isinstance(row, dict) and row.get("name")
    }
    allowed_families = {row.get("name") for row in source_families.get("source_families", []) if isinstance(row, dict) and row.get("name")}
    source_family = plan.get("source_family")
    question_shape = plan.get("question_shape")
    if source_family and source_family not in allowed_families:
        failures.append({"field": "source_family", "reason": f"not allowed: {source_family}"})
    if question_shape and question_shape not in question_shape_policies:
        failures.append({"field": "question_shape", "reason": f"unknown question shape: {question_shape}"})
    if source_family and source_family not in set(acquisition.get("allowed_source_families", [])):
        failures.append({"field": "source_family", "reason": "not present in source-acquisition recipe"})
    if question_shape and source_family and question_shape in question_shape_policies:
        allowed_for_shape = set(question_shape_policies[question_shape].get("allowed_source_families", []))
        if source_family not in allowed_for_shape:
            failures.append({"field": "source_family", "reason": f"not allowed for question_shape {question_shape}: {source_family}"})
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
    search_stage = plan.get("search_stage")
    if search_stage not in {"initial", "refinement"}:
        failures.append({"field": "search_stage", "reason": "must be initial or refinement"})
    query_terms = plan.get("query_terms")
    if not isinstance(query_terms, list) or not query_terms or not all(isinstance(term, str) and term.strip() for term in query_terms):
        failures.append({"field": "query_terms", "reason": "must be a non-empty list of strings"})
    if question_shape in question_shape_policies and isinstance(query_terms, list):
        bounded_search = question_shape_policies[question_shape].get("bounded_search", {})
        initial_budget = bounded_search.get("initial_query_budget")
        refinement_budget = bounded_search.get("refinement_query_budget")
        if search_stage == "initial" and isinstance(initial_budget, int) and len(query_terms) > initial_budget:
            failures.append({"field": "query_terms", "reason": f"initial search exceeds budget for question_shape {question_shape}"})
        if search_stage == "refinement":
            if bounded_search.get("allow_second_stage_refinement") is not True:
                failures.append({"field": "search_stage", "reason": f"refinement not allowed for question_shape {question_shape}"})
            if isinstance(refinement_budget, int) and len(query_terms) > refinement_budget:
                failures.append({"field": "query_terms", "reason": f"refinement search exceeds budget for question_shape {question_shape}"})
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
        "register_provisional_weak_slice",
        "resolve_provisional_weak_slice",
        "check_provenance",
        "check_policy",
        "check_decision_record",
        "check_claim_support",
        "check_exact_wording",
        "check_support_hierarchy",
        "check_confirmation_boundary",
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
    parser.add_argument("--resolution")
    parser.add_argument("--resolution-json")
    parser.add_argument("--resolution-payload")
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
        if args.command == "register_provisional_weak_slice":
            decision_path, error = require_payload_path_or_inline(args.decision_json, args.decision_payload, "decision")
            if error:
                return emit(error)
            assert decision_path is not None
            if args.decision_payload:
                temp_paths.append(decision_path)
            return register_provisional_weak_slice(root, args.term, args.task_type, Path(decision_path))
        if args.command == "resolve_provisional_weak_slice":
            resolution_path = None
            if args.resolution_json or args.resolution_payload:
                path_value, error = require_payload_path_or_inline(args.resolution_json, args.resolution_payload, "resolution")
                if error:
                    return emit(error)
                assert path_value is not None
                resolution_path = Path(path_value)
                if args.resolution_payload:
                    temp_paths.append(path_value)
            return resolve_provisional_weak_slice(root, args.term, args.task_type, args.resolution, resolution_path)
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
        "source/index",
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
    _write(root / "AGENTS.md", AGENTS)
    _write(root / "AUDIT_AGENT.md", AUDIT_GUIDE)
    _write(root / "TESTING.md", TESTING)
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
