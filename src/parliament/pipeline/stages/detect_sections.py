from __future__ import annotations

from parliament.models.document import ExtractedDocument
from parliament.models.section import Section
from parliament.sectioning.heuristics import detect_sections as detect_sections_with_heuristics


def detect_sections(extraction: ExtractedDocument, max_section_chars: int) -> list[Section]:
    return detect_sections_with_heuristics(extraction, max_section_chars=max_section_chars)
