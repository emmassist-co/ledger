from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path


SCRIPT_BODY = """from __future__ import annotations

import argparse
import json
import math
import sqlite3
from pathlib import Path


def load_pdf_hits(archive_root: Path, query: str) -> tuple[list[dict], list[dict]]:
    sqlite_path = archive_root / "source" / "index" / "pdf-pages.sqlite"
    if not sqlite_path.exists():
        return [], []
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            '''
            select p.page_id, p.source_id, p.page_number, p.title, p.source_url, p.raw_pdf_path,
                   p.extracted_markdown_path, p.extracted_json_path, p.snippet
            from pdf_pages_fts f
            join pdf_pages p on p.page_id = f.page_id
            where pdf_pages_fts match ?
            order by bm25(pdf_pages_fts)
            limit 5
            ''',
            (query,),
        ).fetchall()
    finally:
        conn.close()
    hits = []
    metrics = []
    by_source = {}
    for row in rows:
        hits.append(
            {
                "hit_type": "pdf_page",
                "artifact_id": row["page_id"],
                "source_id": row["source_id"],
                "page_number": row["page_number"],
                "title": row["title"],
                "snippet": row["snippet"],
            }
        )
        by_source.setdefault(row["source_id"], set()).add(int(row["page_number"]))
    for source_id, pages in by_source.items():
        extracted_path = archive_root / "source" / "extracted" / f"{source_id}.extracted.md"
        full_pages = extracted_path.read_text(encoding="utf-8").count("# Page ")
        metrics.append(
            {
                "source_id": source_id,
                "full_document_pages": full_pages,
                "selected_pages": len(pages),
                "avoided_pages": max(full_pages - len(pages), 0),
            }
        )
    return hits, metrics


def load_web_hits(archive_root: Path, query: str) -> tuple[list[dict], list[dict]]:
    sqlite_path = archive_root / "source" / "index" / "web-sections.sqlite"
    if not sqlite_path.exists():
        return [], []
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            '''
            select s.section_id, s.source_id, s.section_number, s.title, s.heading, s.source_url,
                   s.markdown_path, s.snippet
            from web_sections_fts f
            join web_sections s on s.section_id = f.section_id
            where web_sections_fts match ?
            order by bm25(web_sections_fts)
            limit 5
            ''',
            (query,),
        ).fetchall()
    finally:
        conn.close()
    hits = []
    metrics = []
    by_source = {}
    for row in rows:
        hits.append(
            {
                "hit_type": "web_section",
                "artifact_id": row["section_id"],
                "source_id": row["source_id"],
                "section_number": row["section_number"],
                "title": row["title"],
                "heading": row["heading"],
                "snippet": row["snippet"],
            }
        )
        by_source.setdefault(row["source_id"], {"sections": 0, "tokens": 0, "path": row["markdown_path"]})
        by_source[row["source_id"]]["sections"] += 1
    for source_id, info in by_source.items():
        markdown_text = Path(info["path"]).read_text(encoding="utf-8")
        total_tokens = len(markdown_text.split())
        metrics.append(
            {
                "source_id": source_id,
                "selected_sections": info["sections"],
                "avoided_tokens": max(total_tokens - len(rows[0]["snippet"].split()), 0),
            }
        )
    return hits, metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-root", required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    archive_root = Path(args.archive_root)
    pdf_hits, pdf_metrics = load_pdf_hits(archive_root, args.question)
    web_hits, web_metrics = load_web_hits(archive_root, args.question)
    hits = web_hits or pdf_hits
    payload = {
        "hits": hits,
        "pdf_retrieval_metrics": pdf_metrics,
        "web_retrieval_metrics": web_metrics,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""


def test_answer_question_includes_pdf_page_hits_and_retrieval_metrics(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive-index"
    (archive_root / "scripts").mkdir(parents=True, exist_ok=True)
    (archive_root / "scripts" / "audit_agent_run.py").write_text(
        "import json\nprint(json.dumps({'ok': True, 'results': []}))\n",
        encoding="utf-8",
    )
    (archive_root / "scripts" / "answer_question.py").write_text(SCRIPT_BODY, encoding="utf-8")

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

    script = archive_root / "scripts" / "answer_question.py"
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
    (archive_root / "scripts" / "answer_question.py").write_text(SCRIPT_BODY, encoding="utf-8")

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

    script = archive_root / "scripts" / "answer_question.py"
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
