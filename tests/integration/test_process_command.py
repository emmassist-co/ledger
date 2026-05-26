from __future__ import annotations

import json
from pathlib import Path

import fitz

from parliament.cli import main


def _build_sample_pdf(path: Path) -> None:
    document = fitz.open()

    page1 = document.new_page()
    page1.insert_text(
        (72, 72),
        "SUMÁRIO\nSessão solene sobre a Ucrânia.\nO Sr. Presidente (PSD): — Está aberta a sessão.",
    )

    page2 = document.new_page()
    page2.insert_text(
        (72, 72),
        "DECLARAÇÃO POLÍTICA DO PCP\nA Sr.ª Paula Santos (PCP): — O custo de vida aumentou.",
    )

    document.save(path)
    document.close()


def test_process_command_generates_expected_document_workspace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pdf_path = tmp_path / "DAR-I-TEST.pdf"
    output_root = tmp_path / "documents"
    _build_sample_pdf(pdf_path)
    monkeypatch.setenv("PARLIAMENT_FAKE_LLM_OUTPUT", "Texto gerado")

    exit_code = main(
        [
            "process",
            str(pdf_path),
            "--output-root",
            str(output_root),
        ]
    )

    document_root = output_root / "DAR-I-TEST"
    assert exit_code == 0
    assert (document_root / "source" / "extracted_text.md").exists()
    episode_files = sorted((document_root / "episodes").glob("*.md"))
    assert len(episode_files) == 2
    assert (document_root / "claims" / "index.md").exists()
    assert "Texto gerado" in (document_root / "views" / "level-1-simple.md").read_text()
    assert "Texto gerado" in episode_files[0].read_text()

    metadata = json.loads((document_root / "metadata.json").read_text())
    assert metadata["document_id"] == "DAR-I-TEST"


def test_process_command_can_resume_after_partial_note_batch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pdf_path = tmp_path / "DAR-I-TEST.pdf"
    output_root = tmp_path / "documents"
    _build_sample_pdf(pdf_path)
    monkeypatch.setenv("PARLIAMENT_FAKE_LLM_OUTPUT", "Texto gerado")

    partial_exit_code = main(
        [
            "process",
            str(pdf_path),
            "--output-root",
            str(output_root),
            "--max-sections",
            "1",
        ]
    )

    document_root = output_root / "DAR-I-TEST"
    assert partial_exit_code == 0
    episode_files = sorted((document_root / "episodes").glob("*.md"))
    assert len(episode_files) == 1
    assert not (document_root / "views" / "level-1-simple.md").exists()

    partial_metadata = json.loads((document_root / "metadata.json").read_text())
    assert partial_metadata["run_status"] == "partial"
    assert partial_metadata["completed_episode_count"] == 1
    assert partial_metadata["episode_count"] == 2

    resumed_exit_code = main(
        [
            "process",
            str(pdf_path),
            "--output-root",
            str(output_root),
            "--resume",
        ]
    )

    assert resumed_exit_code == 0
    assert len(sorted((document_root / "episodes").glob("*.md"))) == 2
    assert "Texto gerado" in (document_root / "views" / "level-1-simple.md").read_text()

    final_metadata = json.loads((document_root / "metadata.json").read_text())
    assert final_metadata["run_status"] == "complete"
    assert final_metadata["completed_episode_count"] == 2


def test_explorer_command_generates_html_for_processed_document(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pdf_path = tmp_path / "DAR-I-TEST.pdf"
    output_root = tmp_path / "documents"
    _build_sample_pdf(pdf_path)
    monkeypatch.setenv("PARLIAMENT_FAKE_LLM_OUTPUT", "Texto gerado")

    process_exit_code = main(
        [
            "process",
            str(pdf_path),
            "--output-root",
            str(output_root),
        ]
    )
    assert process_exit_code == 0

    explorer_exit_code = main(
        [
            "explorer",
            str(output_root / "DAR-I-TEST"),
        ]
    )

    explorer_path = output_root / "DAR-I-TEST" / "explorer.html"
    assert explorer_exit_code == 0
    assert explorer_path.exists()
    html = explorer_path.read_text()
    assert "Parliament Explorer" in html
    assert "Texto gerado" in html
