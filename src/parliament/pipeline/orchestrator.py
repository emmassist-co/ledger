from __future__ import annotations

from pathlib import Path

from parliament.pipeline.stages.detect_sections import detect_sections
from parliament.pipeline.stages.extract_claims_and_references import (
    extract_claims_and_references,
)
from parliament.pipeline.stages.parse_pdf import parse_pdf
from parliament.pipeline.stages.render_views import render_views
from parliament.pipeline.stages.write_index import write_index
from parliament.pipeline.stages.write_section_notes import write_section_notes


def run_pipeline(
    *,
    pdf_path: Path,
    document_id: str,
    max_section_chars: int,
    note_generator,
    claims_generator,
    index_generator,
    view_generators: dict[str, object],
) -> dict[str, object]:
    extraction = parse_pdf(pdf_path, document_id)
    sections = detect_sections(extraction, max_section_chars=max_section_chars)
    notes = write_section_notes(sections, note_generator)
    claims_markdown, references_markdown = extract_claims_and_references(
        document_id,
        notes,
        claims_generator,
    )
    fetched_sources_markdown = "# Fetched sources\n\nNot run.\n"
    views = render_views(
        document_id=document_id,
        notes=notes,
        claims_markdown=claims_markdown,
        fetched_sources_markdown=fetched_sources_markdown,
        generators=view_generators,
    )
    index_markdown = write_index(
        document_id,
        notes,
        claims_markdown,
        index_generator,
    )
    return {
        "extraction": extraction,
        "sections": sections,
        "notes": notes,
        "claims_markdown": claims_markdown,
        "references_markdown": references_markdown,
        "fetched_sources_markdown": fetched_sources_markdown,
        "views": views,
        "index_markdown": index_markdown,
    }
