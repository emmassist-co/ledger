from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from parliament.archive_index.navigation import rebuild_navigation_index
from parliament.archive_index.paths import ArchiveIndexPaths
from parliament.archive_index.artifacts import write_archive_artifact


def test_rebuild_navigation_index_scans_dar_and_dr_artifacts(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive-index"
    paths = ArchiveIndexPaths(archive_root)

    write_archive_artifact(
        path=paths.corpus("dar").registry_dir / "reg-dar-i-001.md",
        frontmatter={
            "artifact_type": "registry",
            "artifact_id": "reg-dar-i-001",
            "source_system": "parlamento.pt",
            "source_url": "https://www.parlamento.pt/example",
            "doc_id": "DAR-I-001",
            "confidence": "high",
            "linked_ids": ["reg-dr-lei-13-2023"],
        },
        body="# DAR I Série n.º 001\n",
    )
    write_archive_artifact(
        path=paths.corpus("dr").registry_dir / "reg-dr-lei-13-2023.md",
        frontmatter={
            "artifact_type": "registry",
            "artifact_id": "reg-dr-lei-13-2023",
            "source_system": "diariodarepublica.pt",
            "source_url": "https://diariodarepublica.pt/dr/detalhe/parlamento/13-2023-211340863",
            "normalized_date": "2023-04-03",
            "doc_id": "LEI-13-2023",
            "confidence": "high",
            "linked_ids": [],
        },
        body="# Lei n.º 13/2023, de 3 de abril\n",
    )

    result = rebuild_navigation_index(paths)

    assert result.document_count == 2
    assert result.link_count == 1
    assert result.documents_jsonl_path == archive_root / "index" / "documents.jsonl"
    assert result.links_jsonl_path == archive_root / "index" / "links.jsonl"
    assert result.sqlite_path == archive_root / "index" / "navigation.sqlite"

    rows = [json.loads(line) for line in result.documents_jsonl_path.read_text().splitlines()]
    assert {row["artifact_id"] for row in rows} == {"reg-dar-i-001", "reg-dr-lei-13-2023"}

    conn = sqlite3.connect(result.sqlite_path)
    documents = list(conn.execute("select artifact_id, normalized_date from documents order by artifact_id"))
    links = list(conn.execute("select from_id, to_id from links"))
    conn.close()

    assert documents == [("reg-dar-i-001", ""), ("reg-dr-lei-13-2023", "2023-04-03")]
    assert links == [("reg-dar-i-001", "reg-dr-lei-13-2023")]


def test_rebuild_navigation_index_skips_non_artifact_markdown_files(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive-index"
    paths = ArchiveIndexPaths(archive_root)

    write_archive_artifact(
        path=paths.corpus("dr").facets_dir / "facet-serie-i.md",
        frontmatter={
            "artifact_type": "facet",
            "artifact_id": "facet-serie-i",
            "source_system": "diariodarepublica.pt",
            "source_url": "https://diariodarepublica.pt/dr/legislacao-por-data",
            "confidence": "high",
            "linked_ids": [],
        },
        body="# I\n",
    )
    readme_path = archive_root / "artifacts" / "extracts" / "README.md"
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text("# Extracts\n\nThis folder stores extract artifacts.\n", encoding="utf-8")

    result = rebuild_navigation_index(paths)

    rows = [json.loads(line) for line in result.documents_jsonl_path.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["artifact_id"] == "facet-serie-i"
    assert rows[0]["source_url"] == "https://diariodarepublica.pt/dr/legislacao-por-data"
