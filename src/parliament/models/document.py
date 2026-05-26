from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedPage:
    document_id: str
    page_number: int
    markdown: str


@dataclass(frozen=True)
class ExtractedDocument:
    document_id: str
    pages: list[ExtractedPage]
    full_markdown: str
