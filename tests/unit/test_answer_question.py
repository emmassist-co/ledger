from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_answer_question_includes_pdf_page_hits_and_retrieval_metrics(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive-index"
    (archive_root / "scripts").mkdir(parents=True, exist_ok=True)
    (archive_root / "scripts" / "audit_agent_run.py").write_text(
        "import json\nprint(json.dumps({'ok': True, 'results': []}))\n",
        encoding="utf-8",
    )

    extracted_dir = archive_root / "source" / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    extracted_markdown_path = extracted_dir / "dar-i-016.extracted.md"
    extracted_markdown_path.write_text(
        "# Page 1\n\nSegurança Social e Administração Pública.\n\n# Page 2\n\nOutro tema.\n",
        encoding="utf-8",
    )

    source_index_dir = archive_root / "source" / "index"
    source_index_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(source_index_dir / "pdf-pages.sqlite")
    conn.execute(
        "create table pdf_pages (page_id text primary key, source_id text, page_number integer, title text, source_url text, raw_pdf_path text, extracted_markdown_path text, extracted_json_path text, search_text text, snippet text)"
    )
    conn.execute("create virtual table pdf_pages_fts using fts5(page_id, source_id, title, search_text)")
    row = {
        "page_id": "dar-i-016#page-1",
        "source_id": "dar-i-016",
        "page_number": 1,
        "title": "DAR I 016",
        "source_url": "https://example.org/dar-i-016.pdf",
        "raw_pdf_path": str(archive_root / "source" / "downloads" / "DAR-I-016.pdf"),
        "extracted_markdown_path": str(extracted_markdown_path),
        "extracted_json_path": str(extracted_dir / "dar-i-016.extracted.json"),
        "search_text": "dar-i-016 DAR I 016 page 1 Segurança Social Administração Pública",
        "snippet": "Segurança Social e Administração Pública.",
    }
    conn.execute(
        "insert into pdf_pages values (:page_id, :source_id, :page_number, :title, :source_url, :raw_pdf_path, :extracted_markdown_path, :extracted_json_path, :search_text, :snippet)",
        row,
    )
    conn.execute(
        "insert into pdf_pages_fts values (:page_id, :source_id, :title, :search_text)",
        row,
    )
    conn.commit()
    conn.close()

    nav_dir = archive_root / "index"
    nav_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(nav_dir / "navigation.sqlite")
    conn.execute(
        "create table documents (artifact_id text primary key, artifact_type text, path text, title text, source_system text, source_url text, normalized_date text, doc_id text, confidence text, search_text text)"
    )
    conn.execute("create virtual table documents_fts using fts5(artifact_id, title, search_text)")
    conn.commit()
    conn.close()

    script = Path("/Users/alexandre/dev/parliament/archive-index/scripts/answer_question.py")
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--archive-root",
            str(archive_root),
            "--question",
            "seguranca social administracao publica",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["hits"][0]["hit_type"] == "pdf_page"
    assert payload["hits"][0]["page_number"] == 1
    assert payload["pdf_retrieval_metrics"][0]["full_document_pages"] == 2
    assert payload["pdf_retrieval_metrics"][0]["selected_pages"] == 1
    assert payload["pdf_retrieval_metrics"][0]["avoided_pages"] == 1


def test_answer_question_prefers_web_section_hits_and_reports_web_metrics(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive-index"
    (archive_root / "scripts").mkdir(parents=True, exist_ok=True)
    (archive_root / "scripts" / "audit_agent_run.py").write_text(
        "import json\nprint(json.dumps({'ok': True, 'results': []}))\n",
        encoding="utf-8",
    )

    markdown_path = archive_root / "source" / "downloads" / "faq-00566.md"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(
        "# FAQ 5869\n\nTexto introdutório.\n\n## Mais-valias\n\nAs tornas constituem um ganho sujeito a IRS e devem constar do Anexo G.\n",
        encoding="utf-8",
    )

    source_index_dir = archive_root / "source" / "index"
    source_index_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(source_index_dir / "web-sections.sqlite")
    conn.execute(
        "create table web_sections (section_id text primary key, source_id text, section_number integer, title text, heading text, source_url text, markdown_path text, search_text text, snippet text)"
    )
    conn.execute("create virtual table web_sections_fts using fts5(section_id, source_id, title, heading, search_text)")
    row = {
        "section_id": "faq-00566#section-2",
        "source_id": "faq-00566",
        "section_number": 2,
        "title": "IRS > Mais-valias",
        "heading": "Mais-valias",
        "source_url": "https://example.org/faq-00566",
        "markdown_path": str(markdown_path),
        "search_text": "faq-00566 IRS Mais-valias tornas ganho sujeito a IRS Anexo G partilha bens imoveis",
        "snippet": "As tornas constituem um ganho sujeito a IRS e devem constar do Anexo G.",
    }
    conn.execute(
        "insert into web_sections values (:section_id, :source_id, :section_number, :title, :heading, :source_url, :markdown_path, :search_text, :snippet)",
        row,
    )
    conn.execute(
        "insert into web_sections_fts values (:section_id, :source_id, :title, :heading, :search_text)",
        row,
    )
    conn.commit()
    conn.close()

    nav_dir = archive_root / "index"
    nav_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(nav_dir / "navigation.sqlite")
    conn.execute(
        "create table documents (artifact_id text primary key, artifact_type text, path text, title text, source_system text, source_url text, normalized_date text, doc_id text, confidence text, search_text text)"
    )
    conn.execute("create virtual table documents_fts using fts5(artifact_id, title, search_text)")
    conn.commit()
    conn.close()

    script = Path("/Users/alexandre/dev/parliament/archive-index/scripts/answer_question.py")
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--archive-root",
            str(archive_root),
            "--question",
            "tornas IRS Anexo G partilha bens imoveis",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["hits"][0]["hit_type"] == "web_section"
    assert payload["hits"][0]["artifact_id"] == "faq-00566#section-2"
    assert payload["web_retrieval_metrics"][0]["source_id"] == "faq-00566"
    assert payload["web_retrieval_metrics"][0]["selected_sections"] == 1
    assert payload["web_retrieval_metrics"][0]["avoided_tokens"] > 0
