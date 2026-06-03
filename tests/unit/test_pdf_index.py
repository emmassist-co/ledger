from __future__ import annotations

import json
from pathlib import Path

from ledger.archive_index import pdf_index


def test_render_and_parse_extracted_pdf_markdown_round_trip() -> None:
    pages = [
        pdf_index.PdfPage(page_number=1, text="Primeira pagina."),
        pdf_index.PdfPage(page_number=2, text="Segunda pagina."),
    ]

    markdown = pdf_index.render_extracted_pdf_markdown(pages)
    parsed = pdf_index.parse_extracted_pdf_markdown(markdown)

    assert parsed == pages


def test_extract_and_index_pdf_writes_markdown_and_searchable_page_index(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "archive-index"
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-pretend")

    monkeypatch.setattr(
        pdf_index,
        "read_pdf_pages_with_liteparse",
        lambda pdf_path, extracted_json_path: [
            pdf_index.PdfPage(page_number=1, text="Lei do trabalho e contrato."),
            pdf_index.PdfPage(page_number=2, text="Regra de salario minimo e ferias."),
        ],
    )

    result = pdf_index.extract_and_index_pdf(
        root=root,
        source_id="dar-i-016",
        pdf_path=pdf_path,
        source_url="https://example.org/dar-i-016.pdf",
        title="DAR I 016",
    )

    assert result.page_count == 2
    assert result.extracted_json_path == root / "source" / "extracted" / "dar-i-016.extracted.json"
    assert result.extracted_markdown_path.read_text(encoding="utf-8").startswith("# Page 1")

    rows = [json.loads(line) for line in result.pages_jsonl_path.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["page_number"] == 1
    assert rows[1]["snippet"].startswith("Regra de salario minimo")
    assert rows[0]["extracted_markdown_path"] == "source/extracted/dar-i-016.extracted.md"

    hits = pdf_index.search_pdf_pages(root=root, query="salario minimo", limit=5)
    assert len(hits) == 1
    assert hits[0].source_id == "dar-i-016"
    assert hits[0].page_number == 2
    assert hits[0].extracted_markdown_path == "source/extracted/dar-i-016.extracted.md"

    manifest_rows = [
        json.loads(line) for line in (root / "source" / "manifests" / "pdf_pages.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert manifest_rows[0]["extracted_markdown_path"] == "source/extracted/dar-i-016.extracted.md"
    assert manifest_rows[0]["pages_jsonl_path"] == "source/index/pdf-pages/dar-i-016.jsonl"
    assert manifest_rows[0]["sqlite_path"] == "source/index/pdf-pages.sqlite"


def test_index_extracted_pdf_rebuilds_shared_sqlite_index(tmp_path: Path) -> None:
    root = tmp_path / "archive-index"
    extracted_dir = root / "source" / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    (extracted_dir / "alpha.extracted.md").write_text(
        "# Page 1\n\nContrato de trabalho.\n\n# Page 2\n\nFaltas justificadas.\n",
        encoding="utf-8",
    )
    (extracted_dir / "beta.extracted.md").write_text(
        "# Page 1\n\nImposto sobre rendimento.\n",
        encoding="utf-8",
    )

    pdf_index.index_extracted_pdf(
        root=root,
        source_id="alpha",
        extracted_markdown_path=Path("source/extracted/alpha.extracted.md"),
        title="Alpha",
    )
    pdf_index.index_extracted_pdf(
        root=root,
        source_id="beta",
        extracted_markdown_path=Path("source/extracted/beta.extracted.md"),
        title="Beta",
    )

    alpha_hits = pdf_index.search_pdf_pages(root=root, query="faltas", source_id="alpha", limit=5)
    beta_hits = pdf_index.search_pdf_pages(root=root, query="imposto", limit=5)

    assert [hit.page_number for hit in alpha_hits] == [2]
    assert [hit.source_id for hit in beta_hits] == ["beta"]


def test_search_pdf_pages_matches_ascii_query_against_accented_text(tmp_path: Path) -> None:
    root = tmp_path / "archive-index"
    extracted_dir = root / "source" / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    (extracted_dir / "gamma.extracted.md").write_text(
        "# Page 1\n\nSegurança Social e Administração Pública.\n",
        encoding="utf-8",
    )

    pdf_index.index_extracted_pdf(
        root=root,
        source_id="gamma",
        extracted_markdown_path=Path("source/extracted/gamma.extracted.md"),
        title="Gamma",
    )

    hits = pdf_index.search_pdf_pages(
        root=root,
        query="seguranca administracao publica",
        source_id="gamma",
        limit=5,
    )

    assert [hit.page_number for hit in hits] == [1]


def test_text_from_liteparse_items_builds_page_text() -> None:
    text = pdf_index.text_from_liteparse_items(
        [
            {"text": "Segurança Social"},
            {"text": "Administração Pública"},
        ]
    )

    assert text == "Segurança Social\nAdministração Pública"
