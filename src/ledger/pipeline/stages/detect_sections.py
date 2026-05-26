from __future__ import annotations

from ledger.models.document import ExtractedDocument
from ledger.models.section import Section
from ledger.sectioning.heuristics import detect_sections as detect_sections_with_heuristics


def detect_sections(extraction: ExtractedDocument, max_section_chars: int) -> list[Section]:
    return detect_sections_with_heuristics(extraction, max_section_chars=max_section_chars)
