from __future__ import annotations

import json
from pathlib import Path

from ledger.archive_index.pdf_index import search_pdf_pages
from ledger.archive_index.source_indexes import rebuild_source_indexes
from ledger.archive_index.web_index import search_web_sections


def test_rebuild_source_indexes_rebuilds_pdf_and_web_indexes(tmp_path: Path) -> None:
    root = tmp_path / "archive-index"
    downloads_dir = root / "source" / "downloads"
    extracted_dir = root / "source" / "extracted"
    manifests_dir = root / "source" / "manifests"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    extracted_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    (downloads_dir / "example.md").write_text(
        "# Example\n\n## Como usar\n\nLeve os documentos necessários.\n",
        encoding="utf-8",
    )
    (extracted_dir / "dar-i-016.extracted.md").write_text(
        "# Page 1\n\nContrato de trabalho.\n\n# Page 2\n\nSalário mínimo nacional.\n",
        encoding="utf-8",
    )
    (manifests_dir / "downloads.jsonl").write_text(
        json.dumps(
            {
                "kind": "source_capture",
                "source_id": "example",
                "source_url": "https://example.com/page",
                "content_format": "markdown",
                "local_path": "archive-index/source/downloads/example.md",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (manifests_dir / "pdf_pages.jsonl").write_text(
        json.dumps(
            {
                "kind": "pdf_page_index",
                "source_id": "dar-i-016",
                "title": "DAR I 016",
                "source_url": "https://example.com/dar-i-016.pdf",
                "raw_pdf_path": "archive-index/source/downloads/DAR-I-016.pdf",
                "extracted_markdown_path": "archive-index/source/extracted/dar-i-016.extracted.md",
                "extracted_json_path": "",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = rebuild_source_indexes(root)

    assert result.web_sources == 1
    assert result.pdf_sources == 1
    assert result.web_index_sqlite.exists()
    assert result.pdf_index_sqlite.exists()

    web_hits = search_web_sections(root=root, query="documentos necessarios", limit=3)
    pdf_hits = search_pdf_pages(root=root, query="salario minimo", limit=3)

    assert web_hits
    assert web_hits[0].markdown_path == "source/downloads/example.md"
    assert pdf_hits
    assert pdf_hits[0].extracted_markdown_path == "source/extracted/dar-i-016.extracted.md"
