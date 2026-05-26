from __future__ import annotations

from pathlib import Path

from parliament.extract.pdf_text import extract_pdf
from parliament.models.document import ExtractedDocument


def parse_pdf(pdf_path: Path, document_id: str) -> ExtractedDocument:
    return extract_pdf(pdf_path, document_id)
