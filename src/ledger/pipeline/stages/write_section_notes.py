from __future__ import annotations

import ast

from ledger.llm.json_utils import extract_json_object
from ledger.models.artifacts import SectionNote
from ledger.models.section import Section


def write_section_notes(sections: list[Section], generator) -> list[SectionNote]:
    notes: list[SectionNote] = []
    for section in sections:
        prompt = "\n".join(
            [
                "You are processing one section of a Portuguese parliamentary transcript.",
                "Return JSON only. Write the content fields in Portuguese.",
                "Rules:",
                "- Distinguish transcript-established facts from speaker claims.",
                "- Do not verify external claims.",
                "- Preserve parties, actors, and evidence pointers.",
                "- Keep evidence pointers short and page-anchored.",
                "- `importance` must be exactly one of: low, medium, high.",
                "- `main_actors`, `party_positions`, `important_claims`, and `external_references_to_check` must be plain Portuguese prose, not JSON or Python literals.",
                "",
                f"Section ID: {section.section_id}",
                f"Title: {section.title}",
                f"Type: {section.section_type}",
                f"Pages: {section.start_page}-{section.end_page}",
                "",
                "Section text:",
                section.text,
                "",
                "Return JSON only with keys:",
                "topics, actors, parties, importance, external_refs, what_happened, why_it_mattered, main_actors, party_positions, important_claims, external_references_to_check, evidence_pointers",
            ]
        )
        generated = extract_json_object(generator.generate(prompt))
        notes.append(
            SectionNote(
                document_id=section.document_id,
                section_id=section.section_id,
                title=section.title,
                section_type=section.section_type,
                pages=[section.start_page, section.end_page],
                topics=_coerce_string_list(generated.get("topics", [])),
                actors=_coerce_string_list(generated.get("actors", [])),
                parties=_coerce_string_list(generated.get("parties", [])),
                importance=_coerce_importance(generated.get("importance", "medium")),
                external_refs=_coerce_string_list(generated.get("external_refs", [])),
                what_happened=_coerce_text(generated.get("what_happened", "")),
                why_it_mattered=_coerce_text(generated.get("why_it_mattered", "")),
                main_actors=_coerce_text(generated.get("main_actors", "")),
                party_positions=_coerce_text(generated.get("party_positions", "")),
                important_claims=_coerce_text(generated.get("important_claims", "")),
                external_references_to_check=_coerce_text(
                    generated.get("external_references_to_check", "")
                ),
                evidence_pointers=_coerce_string_list(generated.get("evidence_pointers", []))
                or [
                    f"Page {page}: supporting passage in source section."
                    for page in section.source_pages
                ],
            )
        )
    return notes


def _coerce_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parsed = _try_parse_literal(value)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        if value.strip():
            return [value.strip()]
    return []


def _coerce_text(value: object) -> str:
    if isinstance(value, str):
        parsed = _try_parse_literal(value)
        if isinstance(parsed, list):
            return "; ".join(str(item).strip() for item in parsed if str(item).strip())
        if isinstance(parsed, dict):
            return "; ".join(f"{key}: {val}" for key, val in parsed.items())
        return value.strip()
    if isinstance(value, list):
        return "; ".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, dict):
        return "; ".join(f"{key}: {val}" for key, val in value.items())
    return str(value).strip()


def _coerce_importance(value: object) -> str:
    normalized = str(value).strip().lower()
    if normalized in {"low", "medium", "high"}:
        return normalized
    return "medium"


def _try_parse_literal(value: str) -> object:
    stripped = value.strip()
    if not stripped or stripped[0] not in "[{(":
        return value
    try:
        return ast.literal_eval(stripped)
    except Exception:
        return value
