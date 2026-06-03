from __future__ import annotations

import json
from pathlib import Path

from ledger.archive_index.web_index import index_markdown_webpage, search_web_sections


def test_index_markdown_webpage_creates_searchable_sections(tmp_path: Path) -> None:
    root = tmp_path / "archive-index"
    markdown_path = root / "source" / "downloads" / "example.md"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(
        "\n".join(
            [
                "# Balcão Heranças",
                "",
                "Este serviço permite identificar os herdeiros.",
                "",
                "## Como usar",
                "",
                "Leve os documentos necessários e faça o registo dos bens.",
                "",
                "## Custos",
                "",
                "O valor depende dos atos pedidos.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = index_markdown_webpage(
        root=root,
        source_id="example",
        markdown_path=Path("source/downloads/example.md"),
        source_url="https://example.com/herancas",
    )

    assert result.section_count == 3
    assert result.sections_jsonl_path.exists()
    assert result.sqlite_path.exists()

    hits = search_web_sections(root=root, query="registo dos bens documentos necessarios", limit=3)
    assert hits
    assert hits[0].source_id == "example"
    assert "Como usar" in hits[0].heading
    assert "registo dos bens" in hits[0].snippet
    assert hits[0].markdown_path == "source/downloads/example.md"

    manifest_rows = [
        json.loads(line) for line in (root / "source" / "manifests" / "web_sections.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert manifest_rows[0]["markdown_path"] == "source/downloads/example.md"
    assert manifest_rows[0]["sections_jsonl_path"] == "source/index/web-sections/example.jsonl"
    assert manifest_rows[0]["sqlite_path"] == "source/index/web-sections.sqlite"
