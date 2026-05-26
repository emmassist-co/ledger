from __future__ import annotations

from pathlib import Path

import fitz
from pymupdf4llm import to_markdown

from ledger.models.document import ExtractedDocument, ExtractedPage


def extract_pdf(pdf_path: Path, document_id: str) -> ExtractedDocument:
    pages = _extract_markdown_pages(pdf_path, document_id)
    full_markdown = "\n\n".join(
        f"# Page {page.page_number}\n\n{page.markdown}".strip() for page in pages
    )
    return ExtractedDocument(
        document_id=document_id,
        pages=pages,
        full_markdown=full_markdown,
    )


def _extract_markdown_pages(pdf_path: Path, document_id: str) -> list[ExtractedPage]:
    document = fitz.open(pdf_path)
    try:
        if _is_text_native_pdf(document):
            return _extract_text_native_pages(document, document_id)
    finally:
        document.close()

    try:
        page_chunks = to_markdown(pdf_path, page_chunks=True)
        pages = [
            ExtractedPage(
                document_id=document_id,
                page_number=chunk["metadata"]["page_number"],
                markdown=_normalize_markdown(chunk["text"]),
            )
            for chunk in page_chunks
        ]
        if any(page.markdown for page in pages):
            return pages
    except Exception:
        pass

    document = fitz.open(pdf_path)
    try:
        return _extract_text_native_pages(document, document_id)
    finally:
        document.close()


def _is_text_native_pdf(document: fitz.Document) -> bool:
    sample_count = min(5, len(document))
    if sample_count == 0:
        return False
    total_words = 0
    total_chars = 0
    for index in range(sample_count):
        page = document[index]
        total_words += len(page.get_text("words"))
        total_chars += len(page.get_text("text").strip())
    average_words = total_words / sample_count
    average_chars = total_chars / sample_count
    return average_words >= 40 or average_chars >= 250


def _extract_text_native_pages(document: fitz.Document, document_id: str) -> list[ExtractedPage]:
    return [
        ExtractedPage(
            document_id=document_id,
            page_number=page.number + 1,
            markdown=_normalize_markdown(_page_text_with_tables(page)),
        )
        for page in document
    ]


def _page_text_with_tables(page: fitz.Page) -> str:
    text = page.get_text("text")
    table_markdown = _extract_table_markdown(page)
    if table_markdown:
        return f"{text.rstrip()}\n\n{table_markdown}".strip()
    return text


def _extract_table_markdown(page: fitz.Page) -> str:
    if not hasattr(page, "find_tables"):
        return ""
    try:
        table_finder = page.find_tables()
    except Exception:
        return ""
    tables = getattr(table_finder, "tables", [])
    rendered = []
    for table in tables:
        rows = table.extract()
        markdown = _rows_to_markdown_table(rows)
        if markdown:
            rendered.append(markdown)
    return "\n\n".join(rendered).strip()


def _rows_to_markdown_table(rows: list[list[str | None]]) -> str:
    cleaned_rows = [
        [str(cell).strip() if cell is not None else "" for cell in row]
        for row in rows
        if any((str(cell).strip() if cell is not None else "") for cell in row)
    ]
    if len(cleaned_rows) < 2:
        return ""
    width = max(len(row) for row in cleaned_rows)
    normalized = [row + [""] * (width - len(row)) for row in cleaned_rows]
    header = normalized[0]
    body = normalized[1:]
    separator = ["---"] * width
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in body)
    return "\n".join(lines)


def _normalize_markdown(markdown: str) -> str:
    normalized = markdown.replace("·", "—")
    lines = [line.rstrip() for line in normalized.splitlines()]
    cleaned = "\n".join(line for line in lines if line.strip())
    return cleaned.strip()
