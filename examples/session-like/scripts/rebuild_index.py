from __future__ import annotations

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
