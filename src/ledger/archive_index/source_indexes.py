from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from ledger.archive_index.pdf_index import index_extracted_pdf
from ledger.archive_index.web_index import first_markdown_title, index_markdown_webpage


@dataclass(frozen=True)
class SourceIndexRebuildResult:
    web_sources: int
    pdf_sources: int
    web_index_sqlite: Path
    pdf_index_sqlite: Path


def rebuild_source_indexes(root: Path) -> SourceIndexRebuildResult:
    pdf_manifest_path = root / "source" / "manifests" / "pdf_pages.jsonl"
    web_manifest_path = root / "source" / "manifests" / "web_sections.jsonl"
    pdf_manifest_rows = _latest_rows_by_source_id(pdf_manifest_path)
    web_manifest_rows = _latest_rows_by_source_id(web_manifest_path)

    pdf_index_dir = root / "source" / "index" / "pdf-pages"
    web_index_dir = root / "source" / "index" / "web-sections"
    pdf_sqlite_path = root / "source" / "index" / "pdf-pages.sqlite"
    web_sqlite_path = root / "source" / "index" / "web-sections.sqlite"

    _reset_directory(pdf_index_dir)
    _reset_directory(web_index_dir)
    _reset_file(pdf_manifest_path)
    _reset_file(web_manifest_path)
    _reset_file(pdf_sqlite_path)
    _reset_file(web_sqlite_path)

    pdf_sources = 0
    pdf_meta = {source_id: row for source_id, row in pdf_manifest_rows.items()}
    for extracted_path in sorted((root / "source" / "extracted").glob("*.extracted.md")):
        relative_path = extracted_path.relative_to(root)
        source_id = extracted_path.name.removesuffix(".extracted.md")
        meta = pdf_meta.get(source_id, {})
        index_extracted_pdf(
            root=root,
            source_id=source_id,
            extracted_markdown_path=relative_path,
            extracted_json_path=_relative_if_present(root, meta.get("extracted_json_path")),
            source_url=str(meta.get("source_url") or ""),
            raw_pdf_path=_absolute_if_present(root, meta.get("raw_pdf_path")),
            title=str(meta.get("title") or source_id),
        )
        pdf_sources += 1

    web_sources = 0
    web_meta = {source_id: row for source_id, row in web_manifest_rows.items()}
    for markdown_path in sorted((root / "source" / "downloads").rglob("*.md")):
        relative_path = markdown_path.relative_to(root)
        source_id = _source_id_for_markdown(relative_path)
        meta = web_meta.get(source_id, {})
        title = str(meta.get("title") or first_markdown_title(markdown_path.read_text(encoding="utf-8")) or source_id)
        index_markdown_webpage(
            root=root,
            source_id=source_id,
            markdown_path=relative_path,
            source_url=str(meta.get("source_url") or ""),
            title=title,
        )
        web_sources += 1

    return SourceIndexRebuildResult(
        web_sources=web_sources,
        pdf_sources=pdf_sources,
        web_index_sqlite=web_sqlite_path,
        pdf_index_sqlite=pdf_sqlite_path,
    )


def _latest_rows_by_source_id(path: Path) -> dict[str, dict]:
    rows_by_source_id: dict[str, dict] = {}
    for row in _load_jsonl(path):
        source_id = str(row.get("source_id") or "").strip()
        if source_id:
            rows_by_source_id[source_id] = row
    return rows_by_source_id


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _relative_if_present(root: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    if path.is_absolute():
        try:
            return path.relative_to(root)
        except ValueError:
            local_candidate = root / "source" / "extracted" / path.name
            return local_candidate.relative_to(root) if local_candidate.exists() else None
    parts = path.parts
    if parts and parts[0] == root.name:
        return Path(*parts[1:])
    return path


def _absolute_if_present(root: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    if path.is_absolute():
        return path if path.exists() else None
    parts = path.parts
    if parts and parts[0] == root.name:
        path = Path(*parts[1:])
    candidate = root / path
    if candidate.exists():
        return candidate
    for fallback in (root / "source" / "cache" / path.name, root / "source" / "downloads" / path.name):
        if fallback.exists():
            return fallback
    return None


def _source_id_for_markdown(relative_path: Path) -> str:
    source_id = relative_path.stem
    if source_id in {"index", "README"} and len(relative_path.parts) > 1:
        return relative_path.parts[-2]
    return source_id


def _reset_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _reset_file(path: Path) -> None:
    path.unlink(missing_ok=True)
