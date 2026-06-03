from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class PdfPage:
    page_number: int
    text: str


@dataclass(frozen=True)
class PdfIndexResult:
    source_id: str
    page_count: int
    extracted_markdown_path: Path
    extracted_json_path: Path | None
    pages_jsonl_path: Path
    sqlite_path: Path


@dataclass(frozen=True)
class PdfSearchHit:
    source_id: str
    page_number: int
    title: str
    source_url: str
    raw_pdf_path: str
    extracted_markdown_path: str
    snippet: str
    rank: float


class PdfIndexError(RuntimeError):
    pass


def extract_and_index_pdf(
    *,
    root: Path,
    source_id: str,
    pdf_path: Path,
    source_url: str = "",
    title: str = "",
    extracted_markdown_path: Path | None = None,
) -> PdfIndexResult:
    relative_extracted_path = extracted_markdown_path or Path("source") / "extracted" / f"{source_id}.extracted.md"
    relative_extracted_json_path = relative_json_path_for_markdown(relative_extracted_path)
    pages = read_pdf_pages_with_liteparse(
        pdf_path=pdf_path,
        extracted_json_path=root / relative_extracted_json_path,
    )
    if not pages:
        raise PdfIndexError(f"No extractable pages found in {pdf_path}")

    if relative_extracted_path.is_absolute():
        raise PdfIndexError("extracted_markdown_path must be relative to the archive root")

    output_path = root / relative_extracted_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_extracted_pdf_markdown(pages), encoding="utf-8")

    return index_extracted_pdf(
        root=root,
        source_id=source_id,
        extracted_markdown_path=relative_extracted_path,
        extracted_json_path=relative_extracted_json_path,
        source_url=source_url,
        raw_pdf_path=pdf_path,
        title=title,
    )


def index_extracted_pdf(
    *,
    root: Path,
    source_id: str,
    extracted_markdown_path: Path,
    extracted_json_path: Path | None = None,
    source_url: str = "",
    raw_pdf_path: Path | None = None,
    title: str = "",
) -> PdfIndexResult:
    if extracted_markdown_path.is_absolute():
        raise PdfIndexError("extracted_markdown_path must be relative to the archive root")

    absolute_extracted_path = root / extracted_markdown_path
    if not absolute_extracted_path.exists():
        raise PdfIndexError(f"Extracted markdown path does not exist: {absolute_extracted_path}")

    pages = parse_extracted_pdf_markdown(absolute_extracted_path.read_text(encoding="utf-8"))
    if not pages:
        raise PdfIndexError(f"No pages found in extracted markdown: {absolute_extracted_path}")

    pages_dir = root / "source" / "index" / "pdf-pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    pages_jsonl_path = pages_dir / f"{source_id}.jsonl"
    page_rows = [
        {
            "source_id": source_id,
            "page_number": page.page_number,
            "title": title or source_id,
            "source_url": source_url,
            "raw_pdf_path": path_value(root, raw_pdf_path),
            "extracted_markdown_path": extracted_markdown_path.as_posix(),
            "extracted_json_path": extracted_json_path.as_posix() if extracted_json_path else "",
            "search_text": build_pdf_page_search_text(source_id=source_id, title=title, page=page),
            "snippet": build_pdf_page_snippet(page.text),
        }
        for page in pages
    ]
    write_jsonl(pages_jsonl_path, page_rows)

    sqlite_path = rebuild_pdf_page_index(root)
    append_pdf_index_manifest(
        root=root,
        source_id=source_id,
        page_count=len(page_rows),
        extracted_markdown_path=extracted_markdown_path,
        extracted_json_path=extracted_json_path,
        pages_jsonl_path=pages_jsonl_path,
        sqlite_path=sqlite_path,
        raw_pdf_path=raw_pdf_path,
        source_url=source_url,
        title=title,
    )
    return PdfIndexResult(
        source_id=source_id,
        page_count=len(page_rows),
        extracted_markdown_path=absolute_extracted_path,
        extracted_json_path=(root / extracted_json_path).resolve() if extracted_json_path else None,
        pages_jsonl_path=pages_jsonl_path,
        sqlite_path=sqlite_path,
    )


def search_pdf_pages(
    *,
    root: Path,
    query: str,
    source_id: str | None = None,
    limit: int = 10,
) -> list[PdfSearchHit]:
    sqlite_path = root / "source" / "index" / "pdf-pages.sqlite"
    if not sqlite_path.exists():
        return []

    fts_query = make_fts_query(query)
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        if source_id:
            rows = conn.execute(
                """
                select
                  p.source_id,
                  p.page_number,
                  p.title,
                  p.source_url,
                  p.raw_pdf_path,
                  p.extracted_markdown_path,
                  p.snippet,
                  bm25(pdf_pages_fts) as rank
                from pdf_pages_fts
                join pdf_pages p on p.page_id = pdf_pages_fts.page_id
                where pdf_pages_fts match ? and p.source_id = ?
                order by rank
                limit ?
                """,
                (fts_query, source_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                select
                  p.source_id,
                  p.page_number,
                  p.title,
                  p.source_url,
                  p.raw_pdf_path,
                  p.extracted_markdown_path,
                  p.snippet,
                  bm25(pdf_pages_fts) as rank
                from pdf_pages_fts
                join pdf_pages p on p.page_id = pdf_pages_fts.page_id
                where pdf_pages_fts match ?
                order by rank
                limit ?
                """,
                (fts_query, limit),
            ).fetchall()
    finally:
        conn.close()

    return [
        PdfSearchHit(
            source_id=row["source_id"],
            page_number=int(row["page_number"]),
            title=row["title"],
            source_url=row["source_url"],
            raw_pdf_path=row["raw_pdf_path"],
            extracted_markdown_path=row["extracted_markdown_path"],
            snippet=row["snippet"],
            rank=float(row["rank"]),
        )
        for row in rows
    ]


def rebuild_pdf_page_index(root: Path) -> Path:
    pages_dir = root / "source" / "index" / "pdf-pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for path in sorted(pages_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))

    sqlite_path = root / "source" / "index" / "pdf-pages.sqlite"
    conn = sqlite3.connect(sqlite_path)
    conn.execute("drop table if exists pdf_pages")
    conn.execute("drop table if exists pdf_pages_fts")
    conn.execute(
        "create table pdf_pages (page_id text primary key, source_id text, page_number integer, title text, source_url text, raw_pdf_path text, extracted_markdown_path text, extracted_json_path text, search_text text, snippet text)"
    )
    conn.execute("create virtual table pdf_pages_fts using fts5(page_id, source_id, title, search_text)")
    conn.executemany(
        "insert into pdf_pages values (:page_id, :source_id, :page_number, :title, :source_url, :raw_pdf_path, :extracted_markdown_path, :extracted_json_path, :search_text, :snippet)",
        [
            {
                "page_id": page_id_for_row(row),
                **row,
            }
            for row in rows
        ],
    )
    conn.executemany(
        "insert into pdf_pages_fts values (:page_id, :source_id, :title, :search_text)",
        [
            {
                "page_id": page_id_for_row(row),
                "source_id": row["source_id"],
                "title": row["title"],
                "search_text": row["search_text"],
            }
            for row in rows
        ],
    )
    conn.commit()
    conn.close()
    return sqlite_path


def append_pdf_index_manifest(
    *,
    root: Path,
    source_id: str,
    page_count: int,
    extracted_markdown_path: Path,
    extracted_json_path: Path | None,
    pages_jsonl_path: Path,
    sqlite_path: Path,
    raw_pdf_path: Path | None,
    source_url: str,
    title: str,
) -> None:
    manifest_path = root / "source" / "manifests" / "pdf_pages.jsonl"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "kind": "pdf_page_index",
        "source_id": source_id,
        "source_url": source_url,
        "title": title or source_id,
        "raw_pdf_path": path_value(root, raw_pdf_path),
        "extracted_markdown_path": extracted_markdown_path.as_posix(),
        "extracted_json_path": extracted_json_path.as_posix() if extracted_json_path else "",
        "pages_jsonl_path": pages_jsonl_path.relative_to(root).as_posix(),
        "sqlite_path": sqlite_path.relative_to(root).as_posix(),
        "page_count": page_count,
        "indexed_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    append_jsonl(manifest_path, row)


def relative_json_path_for_markdown(markdown_path: Path) -> Path:
    stem = markdown_path.name.removesuffix(".md")
    return markdown_path.parent / f"{stem}.json"


def parse_extracted_pdf_markdown(markdown: str) -> list[PdfPage]:
    pattern = re.compile(r"^#{1,2} Page (\d+)\n(.*?)(?=^#{1,2} Page \d+\n|\Z)", re.MULTILINE | re.DOTALL)
    pages = []
    for match in pattern.finditer(markdown.strip()):
        text = match.group(2).strip()
        if text:
            pages.append(PdfPage(page_number=int(match.group(1)), text=text))
    return pages


def render_extracted_pdf_markdown(pages: list[PdfPage]) -> str:
    parts = []
    for page in pages:
        parts.append(f"# Page {page.page_number}\n{page.text.strip()}\n")
    return "\n".join(parts).strip() + "\n"


def read_pdf_pages_with_liteparse(*, pdf_path: Path, extracted_json_path: Path) -> list[PdfPage]:
    parsed = run_liteparse_json(pdf_path=pdf_path, output_path=extracted_json_path)
    pages = []
    for page in parsed.get("pages", []):
        page_number = int(page.get("page_number") or page.get("page") or 0)
        text = str(page.get("text") or "").strip()
        if not text:
            text = text_from_liteparse_items(page.get("text_items"))
        if page_number and text:
            pages.append(PdfPage(page_number=page_number, text=text))
    return pages


def run_liteparse_json(*, pdf_path: Path, output_path: Path) -> dict:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["liteparse", str(pdf_path), "--json", "--output", str(output_path)],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ},
    )
    if completed.returncode != 0:
        raise PdfIndexError(
            f"liteparse failed for {pdf_path}: {completed.stderr.strip() or completed.stdout.strip() or 'unknown error'}"
        )
    try:
        return json.loads(output_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PdfIndexError(f"liteparse returned invalid JSON for {pdf_path}") from exc


def text_from_liteparse_items(items: object) -> str:
    if not isinstance(items, list):
        return ""
    parts = []
    for item in items:
        if isinstance(item, dict):
            value = str(item.get("text") or "").strip()
            if value:
                parts.append(value)
    return "\n".join(parts).strip()


def build_pdf_page_search_text(*, source_id: str, title: str, page: PdfPage) -> str:
    return " ".join(
        token
        for token in [
            normalize_for_search(source_id),
            normalize_for_search(title),
            normalize_for_search(page.text),
        ]
        if token
    )


def build_pdf_page_snippet(text: str, max_chars: int = 280) -> str:
    compact = " ".join(text.split())
    return compact[:max_chars]


def page_id_for_row(row: dict[str, object]) -> str:
    return f"{row['source_id']}#page-{row['page_number']}"


def append_jsonl(path: Path, row: dict[str, object]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def make_fts_query(query: str) -> str:
    tokens = [token for token in tokenize(query) if len(token) >= 3]
    if not tokens:
        return '"query"'
    return " OR ".join(dict.fromkeys(tokens))


def tokenize(text: str) -> list[str]:
    token = []
    tokens = []
    for ch in normalize_for_search(text):
        if ch.isalnum():
            token.append(ch)
        elif token:
            tokens.append("".join(token))
            token = []
    if token:
        tokens.append("".join(token))
    return tokens


def normalize_for_search(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed.lower() if not unicodedata.combining(ch))


def path_value(root: Path, path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
