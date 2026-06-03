from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ledger.archive_index.paths import display_archive_path


@dataclass(frozen=True)
class WebSection:
    heading: str
    text: str


@dataclass(frozen=True)
class WebIndexResult:
    source_id: str
    section_count: int
    markdown_path: Path
    sections_jsonl_path: Path
    sqlite_path: Path


@dataclass(frozen=True)
class WebSearchHit:
    source_id: str
    section_id: str
    title: str
    heading: str
    source_url: str
    markdown_path: str
    snippet: str
    rank: float


class WebIndexError(RuntimeError):
    pass


def index_markdown_webpage(
    *,
    root: Path,
    source_id: str,
    markdown_path: Path,
    source_url: str = "",
    title: str = "",
) -> WebIndexResult:
    if markdown_path.is_absolute():
        raise WebIndexError("markdown_path must be relative to the archive root")

    absolute_markdown_path = root / markdown_path
    if not absolute_markdown_path.exists():
        raise WebIndexError(f"Markdown path does not exist: {absolute_markdown_path}")

    sections = parse_markdown_sections(absolute_markdown_path.read_text(encoding="utf-8"))
    if not sections:
        sections = [WebSection(heading=title or source_id, text=absolute_markdown_path.read_text(encoding="utf-8"))]

    sections_dir = root / "source" / "index" / "web-sections"
    sections_dir.mkdir(parents=True, exist_ok=True)
    sections_jsonl_path = sections_dir / f"{source_id}.jsonl"
    page_title = title or first_markdown_title(absolute_markdown_path.read_text(encoding="utf-8")) or source_id
    stored_markdown_path = display_archive_path(root, absolute_markdown_path)
    rows = [
        {
            "source_id": source_id,
            "section_number": index,
            "title": page_title,
            "heading": section.heading,
            "source_url": source_url,
            "markdown_path": stored_markdown_path,
            "search_text": build_web_section_search_text(
                source_id=source_id,
                title=page_title,
                heading=section.heading,
                text=section.text,
            ),
            "snippet": build_web_section_snippet(section.text),
        }
        for index, section in enumerate(sections, start=1)
    ]
    write_jsonl(sections_jsonl_path, rows)

    sqlite_path = rebuild_web_section_index(root)
    append_web_index_manifest(
        root=root,
        source_id=source_id,
        source_url=source_url,
        title=page_title,
        markdown_path=absolute_markdown_path,
        section_count=len(rows),
        sections_jsonl_path=sections_jsonl_path,
        sqlite_path=sqlite_path,
    )
    return WebIndexResult(
        source_id=source_id,
        section_count=len(rows),
        markdown_path=absolute_markdown_path,
        sections_jsonl_path=sections_jsonl_path,
        sqlite_path=sqlite_path,
    )


def search_web_sections(
    *,
    root: Path,
    query: str,
    source_id: str | None = None,
    limit: int = 10,
) -> list[WebSearchHit]:
    sqlite_path = root / "source" / "index" / "web-sections.sqlite"
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
                  w.source_id,
                  w.section_number,
                  w.title,
                  w.heading,
                  w.source_url,
                  w.markdown_path,
                  w.snippet,
                  bm25(web_sections_fts) as rank
                from web_sections_fts
                join web_sections w on w.section_id = web_sections_fts.section_id
                where web_sections_fts match ? and w.source_id = ?
                order by rank
                limit ?
                """,
                (fts_query, source_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                select
                  w.source_id,
                  w.section_number,
                  w.title,
                  w.heading,
                  w.source_url,
                  w.markdown_path,
                  w.snippet,
                  bm25(web_sections_fts) as rank
                from web_sections_fts
                join web_sections w on w.section_id = web_sections_fts.section_id
                where web_sections_fts match ?
                order by rank
                limit ?
                """,
                (fts_query, limit),
            ).fetchall()
    finally:
        conn.close()

    return [
        WebSearchHit(
            source_id=row["source_id"],
            section_id=f"{row['source_id']}#section-{row['section_number']}",
            title=row["title"],
            heading=row["heading"],
            source_url=row["source_url"],
            markdown_path=row["markdown_path"],
            snippet=row["snippet"],
            rank=float(row["rank"]),
        )
        for row in rows
    ]


def parse_markdown_sections(markdown_text: str) -> list[WebSection]:
    text = markdown_text.strip()
    if not text:
        return []
    lines = text.splitlines()
    sections: list[WebSection] = []
    current_heading = ""
    buffer: list[str] = []

    def flush_buffer() -> None:
        nonlocal buffer
        section_text = "\n".join(buffer).strip()
        buffer = []
        if not section_text:
            return
        for chunk in chunk_markdown_section(section_text):
            sections.append(WebSection(heading=current_heading or "Document", text=chunk))

    for line in lines:
        if re.match(r"^#{1,6}\s+", line):
            flush_buffer()
            current_heading = re.sub(r"^#{1,6}\s+", "", line).strip()
            continue
        if line.strip() == "" and buffer and buffer[-1] == "":
            continue
        buffer.append(line.rstrip())
    flush_buffer()
    return sections


def chunk_markdown_section(text: str, max_chars: int = 1400) -> list[str]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    if not blocks:
        return []
    chunks: list[str] = []
    current = ""
    for block in blocks:
        candidate = f"{current}\n\n{block}".strip() if current else block
        if current and len(candidate) > max_chars:
            chunks.append(current.strip())
            current = block
        else:
            current = candidate
    if current.strip():
        chunks.append(current.strip())
    return chunks


def rebuild_web_section_index(root: Path) -> Path:
    sections_dir = root / "source" / "index" / "web-sections"
    sections_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for path in sorted(sections_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))

    sqlite_path = root / "source" / "index" / "web-sections.sqlite"
    conn = sqlite3.connect(sqlite_path)
    conn.execute("drop table if exists web_sections")
    conn.execute("drop table if exists web_sections_fts")
    conn.execute(
        "create table web_sections (section_id text primary key, source_id text, section_number integer, title text, heading text, source_url text, markdown_path text, search_text text, snippet text)"
    )
    conn.execute("create virtual table web_sections_fts using fts5(section_id, source_id, title, heading, search_text)")
    conn.executemany(
        "insert into web_sections values (:section_id, :source_id, :section_number, :title, :heading, :source_url, :markdown_path, :search_text, :snippet)",
        [{**row, "section_id": section_id_for_row(row)} for row in rows],
    )
    conn.executemany(
        "insert into web_sections_fts values (:section_id, :source_id, :title, :heading, :search_text)",
        [
            {
                "section_id": section_id_for_row(row),
                "source_id": row["source_id"],
                "title": row["title"],
                "heading": row["heading"],
                "search_text": row["search_text"],
            }
            for row in rows
        ],
    )
    conn.commit()
    conn.close()
    return sqlite_path


def first_markdown_title(markdown_text: str) -> str:
    for line in markdown_text.splitlines():
        if re.match(r"^#{1,6}\s+", line):
            return re.sub(r"^#{1,6}\s+", "", line).strip()
    return ""


def build_web_section_search_text(*, source_id: str, title: str, heading: str, text: str) -> str:
    base = " ".join(part for part in [source_id, title, heading, text.replace("\n", " ")] if part).strip()
    folded = fold_text_for_search(base)
    return " ".join(part for part in [base, folded] if part).strip()


def build_web_section_snippet(text: str, limit: int = 280) -> str:
    return re.sub(r"\s+", " ", text).strip()[:limit]


def make_fts_query(text: str) -> str:
    tokens = [token for token in tokenize(fold_text_for_search(text)) if len(token) >= 3]
    if not tokens:
        return '"question"'
    return " OR ".join(dict.fromkeys(tokens))


def tokenize(text: str) -> list[str]:
    token = []
    tokens = []
    for ch in text.lower():
        if ch.isalnum():
            token.append(ch)
        elif token:
            tokens.append("".join(token))
            token = []
    if token:
        tokens.append("".join(token))
    return tokens


def fold_text_for_search(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def append_web_index_manifest(
    *,
    root: Path,
    source_id: str,
    source_url: str,
    title: str,
    markdown_path: Path,
    section_count: int,
    sections_jsonl_path: Path,
    sqlite_path: Path,
) -> None:
    manifest_path = root / "source" / "manifests" / "web_sections.jsonl"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "kind": "web_section_index",
        "source_id": source_id,
        "title": title,
        "source_url": source_url,
        "markdown_path": display_archive_path(root, markdown_path),
        "sections_jsonl_path": display_archive_path(root, sections_jsonl_path),
        "sqlite_path": display_archive_path(root, sqlite_path),
        "section_count": section_count,
        "indexed_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    with manifest_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def section_id_for_row(row: dict[str, object]) -> str:
    return f"{row['source_id']}#section-{row['section_number']}"
