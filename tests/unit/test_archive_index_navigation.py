from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ledger.archive_index.navigation import rebuild_navigation_index
from ledger.archive_index.paths import ArchiveIndexPaths
from ledger.archive_index.artifacts import write_archive_artifact


def test_rebuild_navigation_index_scans_multiple_corpora(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive-index"
    paths = ArchiveIndexPaths(archive_root)

    write_archive_artifact(
        path=paths.corpus("alpha").registry_dir / "reg-alpha-001.md",
        frontmatter={
            "artifact_type": "registry",
            "artifact_id": "reg-alpha-001",
            "source_system": "example.gov",
            "source_url": "https://example.gov/alpha/001",
            "doc_id": "ALPHA-001",
            "confidence": "high",
            "linked_ids": ["reg-beta-2023"],
        },
        body="# Alpha Registry 001\n",
    )
    write_archive_artifact(
        path=paths.corpus("beta").registry_dir / "reg-beta-2023.md",
        frontmatter={
            "artifact_type": "registry",
            "artifact_id": "reg-beta-2023",
            "source_system": "example.org",
            "source_url": "https://example.org/beta/2023",
            "normalized_date": "2023-04-03",
            "doc_id": "BETA-2023",
            "confidence": "high",
            "linked_ids": [],
        },
        body="# Beta Registry 2023\n",
    )

    result = rebuild_navigation_index(paths)

    assert result.document_count == 2
    assert result.link_count == 1
    assert result.documents_jsonl_path == archive_root / "index" / "documents.jsonl"
    assert result.links_jsonl_path == archive_root / "index" / "links.jsonl"
    assert result.sqlite_path == archive_root / "index" / "navigation.sqlite"

    rows = [json.loads(line) for line in result.documents_jsonl_path.read_text().splitlines()]
    assert {row["artifact_id"] for row in rows} == {"reg-alpha-001", "reg-beta-2023"}

    conn = sqlite3.connect(result.sqlite_path)
    documents = list(conn.execute("select artifact_id, normalized_date from documents order by artifact_id"))
    links = list(conn.execute("select from_id, to_id from links"))
    conn.close()

    assert documents == [("reg-alpha-001", ""), ("reg-beta-2023", "2023-04-03")]
    assert links == [("reg-alpha-001", "reg-beta-2023")]


def test_rebuild_navigation_index_skips_non_artifact_markdown_files(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive-index"
    paths = ArchiveIndexPaths(archive_root)

    write_archive_artifact(
        path=paths.corpus("beta").facets_dir / "facet-category-core.md",
        frontmatter={
            "artifact_type": "facet",
            "artifact_id": "facet-category-core",
            "source_system": "example.org",
            "source_url": "https://example.org/beta",
            "confidence": "high",
            "linked_ids": [],
        },
        body="# Core\n",
    )
    readme_path = archive_root / "artifacts" / "extracts" / "README.md"
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text("# Extracts\n\nThis folder stores extract artifacts.\n", encoding="utf-8")

    result = rebuild_navigation_index(paths)

    rows = [json.loads(line) for line in result.documents_jsonl_path.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["artifact_id"] == "facet-category-core"
    assert rows[0]["source_url"] == "https://example.org/beta"
