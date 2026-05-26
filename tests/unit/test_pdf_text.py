from __future__ import annotations

import json
from pathlib import Path

import fitz

from parliament.extract import pdf_text
from parliament.extract.page_map import build_page_map
from parliament.extract.pdf_text import extract_pdf


def _build_sample_pdf(path: Path) -> None:
    document = fitz.open()

    page1 = document.new_page()
    page1.insert_text(
        (72, 72),
        "SUMÁRIO\nSessão solene sobre a Ucrânia\nO Sr. Presidente (PSD): — Está aberta a sessão.\nAplausos do PSD e do PS.",
    )

    page2 = document.new_page()
    page2.insert_text(
        (72, 72),
        "DECLARAÇÃO POLÍTICA DO PCP\nA Sr.ª Paula Santos (PCP): — O custo de vida aumentou.\nProtestos do CH.",
    )

    document.save(path)
    document.close()


def test_extract_pdf_preserves_pages_and_procedural_lines(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    _build_sample_pdf(pdf_path)

    extraction = extract_pdf(pdf_path, "DAR-I-TEST")

    assert extraction.document_id == "DAR-I-TEST"
    assert len(extraction.pages) == 2
    assert extraction.pages[0].page_number == 1
    assert "Aplausos do PSD e do PS." in extraction.pages[0].markdown
    assert "DECLARAÇÃO POLÍTICA DO PCP" in extraction.full_markdown
    assert "# Page 1" in extraction.full_markdown


def test_build_page_map_tracks_page_numbers_and_block_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    _build_sample_pdf(pdf_path)

    extraction = extract_pdf(pdf_path, "DAR-I-TEST")
    page_map = build_page_map(extraction.pages)

    assert page_map["document_id"] == "DAR-I-TEST"
    assert page_map["pages"][0]["page_number"] == 1
    assert "Sessão solene sobre a Ucrânia" in page_map["pages"][0]["text"]

    serialized = json.dumps(page_map, ensure_ascii=False)
    assert "DECLARAÇÃO POLÍTICA DO PCP" in serialized


def test_extract_pdf_prefers_text_native_path_without_markdown_ocr(tmp_path: Path, monkeypatch) -> None:
    pdf_path = tmp_path / "sample.pdf"
    _build_sample_pdf(pdf_path)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("OCR markdown path should not be used for text-native PDFs")

    monkeypatch.setattr(pdf_text, "to_markdown", fail_if_called)

    extraction = extract_pdf(pdf_path, "DAR-I-TEST")

    assert "Sessão solene sobre a Ucrânia" in extraction.pages[0].markdown


def test_rows_to_markdown_table_renders_simple_table() -> None:
    markdown = pdf_text._rows_to_markdown_table(
        [
            ["Partido", "Votos"],
            ["PS", "120"],
            ["PSD", "78"],
        ]
    )

    assert "| Partido | Votos |" in markdown
    assert "| PS | 120 |" in markdown
