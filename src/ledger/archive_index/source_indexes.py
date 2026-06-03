from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from ledger.archive_index.paths import relative_archive_path, resolve_archive_path
from ledger.archive_index.pdf_index import index_extracted_pdf
from ledger.archive_index.web_index import index_markdown_webpage


@dataclass(frozen=True)
class SourceIndexRebuildResult:
    web_sources: int
    pdf_sources: int


def rebuild_source_indexes(root: Path) -> SourceIndexRebuildResult:
    pdf_manifest_path = root / "source" / "manifests" / "pdf_pages.jsonl"
    pdf_rows = _latest_rows_by_source_id(pdf_manifest_path)

    source_index_root = root / "source" / "index"
    _reset_directory(source_index_root / "web-sections")
    _reset_directory(source_index_root / "pdf-pages")
    _reset_file(source_index_root / "web-sections.sqlite")
    _reset_file(source_index_root / "pdf-pages.sqlite")
    _reset_file(root / "source" / "manifests" / "web_sections.jsonl")
    _reset_file(pdf_manifest_path)

    web_sources = 0
    for row in _latest_rows_by_source_id(root / "source" / "manifests" / "downloads.jsonl"):
        if row.get("kind") != "source_capture" or row.get("content_format") != "markdown":
            continue
        source_id = str(row.get("source_id") or "").strip()
        local_path = str(row.get("local_path") or "").strip()
        if not source_id or not local_path:
            continue
        index_markdown_webpage(
            root=root,
            source_id=source_id,
            markdown_path=relative_archive_path(root, local_path),
            source_url=str(row.get("source_url") or "").strip(),
            title=str(row.get("title") or "").strip(),
        )
        web_sources += 1

    pdf_sources = 0
    if pdf_rows:
        for row in pdf_rows:
            source_id = str(row.get("source_id") or "").strip()
            extracted_path = str(row.get("extracted_markdown_path") or "").strip()
            if not source_id or not extracted_path:
                continue
            extracted_json = str(row.get("extracted_json_path") or "").strip()
            raw_pdf = str(row.get("raw_pdf_path") or "").strip()
            index_extracted_pdf(
                root=root,
                source_id=source_id,
                extracted_markdown_path=relative_archive_path(root, extracted_path),
                extracted_json_path=relative_archive_path(root, extracted_json) if extracted_json else None,
                source_url=str(row.get("source_url") or "").strip(),
                raw_pdf_path=resolve_archive_path(root, raw_pdf) if raw_pdf else None,
                title=str(row.get("title") or "").strip(),
            )
            pdf_sources += 1
        return SourceIndexRebuildResult(web_sources=web_sources, pdf_sources=pdf_sources)

    for extracted_path in sorted((root / "source" / "extracted").glob("*.extracted.md")):
        source_id = extracted_path.name.removesuffix(".extracted.md")
        index_extracted_pdf(
            root=root,
            source_id=source_id,
            extracted_markdown_path=relative_archive_path(root, extracted_path),
            title=source_id,
        )
        pdf_sources += 1
    return SourceIndexRebuildResult(web_sources=web_sources, pdf_sources=pdf_sources)


def _latest_rows_by_source_id(path: Path) -> list[dict[str, object]]:
    rows_by_source_id: dict[str, dict[str, object]] = {}
    for row in _iter_jsonl(path):
        source_id = str(row.get("source_id") or "").strip()
        if source_id:
            rows_by_source_id[source_id] = row
    return list(rows_by_source_id.values())


def _iter_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _reset_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _reset_file(path: Path) -> None:
    path.unlink(missing_ok=True)
