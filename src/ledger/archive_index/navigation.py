from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from ledger.archive_index.artifacts import read_archive_artifact
from ledger.archive_index.paths import ArchiveIndexPaths


@dataclass(frozen=True)
class NavigationRebuildResult:
    document_count: int
    link_count: int
    documents_jsonl_path: object
    links_jsonl_path: object
    sqlite_path: object


def rebuild_navigation_index(paths: ArchiveIndexPaths) -> NavigationRebuildResult:
    entries: list[dict[str, object]] = []
    links: list[dict[str, str]] = []
    for path in sorted(paths.artifacts_root.rglob("*.md")):
        try:
            artifact = read_archive_artifact(path)
        except ValueError:
            continue
        metadata = artifact.metadata
        title = artifact.body.strip().splitlines()[0].lstrip("# ").strip() if artifact.body.strip() else str(
            metadata.get("artifact_id", path.stem)
        )
        entry = {
            "artifact_id": str(metadata.get("artifact_id", path.stem)),
            "artifact_type": str(metadata.get("artifact_type", "unknown")),
            "path": str(path),
            "title": title,
            "source_system": str(metadata.get("source_system", "")),
            "source_url": str(metadata.get("source_url", "")),
            "normalized_date": str(metadata.get("normalized_date") or metadata.get("source_date_text") or ""),
            "doc_id": str(metadata.get("doc_id") or ""),
            "confidence": str(metadata.get("confidence") or ""),
            "search_text": " ".join(
                [
                    str(metadata.get("artifact_type", "")),
                    str(metadata.get("doc_id", "")),
                    str(metadata.get("source_title", "")),
                    artifact.body.replace("\n", " ")[:4000],
                ]
            ).strip(),
        }
        entries.append(entry)
        for linked_id in metadata.get("linked_ids", []) or []:
            links.append(
                {
                    "from_id": entry["artifact_id"],
                    "to_id": str(linked_id),
                    "relationship": "linked",
                    "path": str(path),
                }
            )

    paths.index_root.mkdir(parents=True, exist_ok=True)
    documents_jsonl_path = paths.index_root / "documents.jsonl"
    links_jsonl_path = paths.index_root / "links.jsonl"
    sqlite_path = paths.index_root / "navigation.sqlite"

    documents_jsonl_path.write_text("".join(json.dumps(entry, ensure_ascii=False) + "\n" for entry in entries))
    links_jsonl_path.write_text("".join(json.dumps(link, ensure_ascii=False) + "\n" for link in links))

    conn = sqlite3.connect(sqlite_path)
    conn.execute("drop table if exists documents")
    conn.execute("drop table if exists documents_fts")
    conn.execute("drop table if exists links")
    conn.execute(
        "create table documents (artifact_id text primary key, artifact_type text, path text, title text, source_system text, source_url text, normalized_date text, doc_id text, confidence text, search_text text)"
    )
    conn.execute("create virtual table documents_fts using fts5(artifact_id, title, search_text)")
    conn.execute("create table links (from_id text, to_id text, relationship text, path text)")
    conn.executemany(
        "insert into documents values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                entry["artifact_id"],
                entry["artifact_type"],
                entry["path"],
                entry["title"],
                entry["source_system"],
                entry["source_url"],
                entry["normalized_date"],
                entry["doc_id"],
                entry["confidence"],
                entry["search_text"],
            )
            for entry in entries
        ],
    )
    conn.executemany(
        "insert into documents_fts values (?, ?, ?)",
        [(entry["artifact_id"], entry["title"], entry["search_text"]) for entry in entries],
    )
    conn.executemany(
        "insert into links values (?, ?, ?, ?)",
        [(link["from_id"], link["to_id"], link["relationship"], link["path"]) for link in links],
    )
    conn.commit()
    conn.close()

    return NavigationRebuildResult(
        document_count=len(entries),
        link_count=len(links),
        documents_jsonl_path=documents_jsonl_path,
        links_jsonl_path=links_jsonl_path,
        sqlite_path=sqlite_path,
    )
