from __future__ import annotations

import math
import re

from ledger.models.document import ExtractedDocument
from ledger.models.section import Section
from ledger.sectioning.normalizer import slugify

MAX_SECTION_SLUG_LENGTH = 110


def detect_sections(
    extraction: ExtractedDocument,
    *,
    max_section_chars: int,
) -> list[Section]:
    base_sections: list[Section] = []
    for page in extraction.pages:
        fragments = _split_page_into_fragments(page.markdown)
        for fragment in fragments:
            if not fragment.strip():
                continue
            built = _build_section_from_page(extraction.document_id, page.page_number, fragment)
            if built is not None:
                base_sections.append(built)
    base_sections = _merge_adjacent_sections(base_sections)

    sections: list[Section] = []
    index = 0
    for section in base_sections:
        if len(section.text) <= max_section_chars:
            sections.append(
                Section(
                    document_id=section.document_id,
                    section_id=_build_section_id(index, section.title),
                    title=section.title,
                    section_type=section.section_type,
                    start_page=section.start_page,
                    end_page=section.end_page,
                    text=section.text,
                    source_pages=section.source_pages,
                )
            )
            index += 1
            continue

        parts = _split_section(section, max_section_chars)
        for suffix, part in zip(_part_suffixes(len(parts)), parts, strict=True):
            sections.append(
                Section(
                    document_id=section.document_id,
                    section_id=_build_section_id(index, section.title, suffix=f"part-{suffix}"),
                    title=f"{section.title} (Part {suffix.upper()})",
                    section_type=section.section_type,
                    start_page=section.start_page,
                    end_page=section.end_page,
                    text=part,
                    source_pages=section.source_pages,
                )
            )
        index += 1

    return sections


def _build_section_id(index: int, title: str, *, suffix: str | None = None) -> str:
    slug = slugify(title)[:MAX_SECTION_SLUG_LENGTH].strip("-")
    if not slug:
        slug = "section"
    base = f"{index:02d}-{slug}"
    if suffix:
        return f"{base}-{suffix}"
    return base


def _build_section_from_page(document_id: str, page_number: int, markdown: str) -> Section | None:
    cleaned_markdown = _strip_page_furniture(markdown)
    if not cleaned_markdown:
        return None
    heading = cleaned_markdown.splitlines()[0].replace("#", "").strip()
    title, section_type = _classify_heading(heading, cleaned_markdown)
    return Section(
        document_id=document_id,
        section_id="",
        title=title,
        section_type=section_type,
        start_page=page_number,
        end_page=page_number,
        text=cleaned_markdown,
        source_pages=[page_number],
    )


def _split_page_into_fragments(markdown: str) -> list[str]:
    lines = [line.rstrip() for line in markdown.splitlines() if line.strip()]
    if not lines:
        return []

    fragments: list[list[str]] = [[]]
    for line in lines:
        if _speaker_line_starts_new_fragment(line, fragments[-1]):
            handoff_lines = _extract_trailing_handoff_lines(fragments[-1])
            if handoff_lines and fragments[-1]:
                fragments.append([*handoff_lines, line])
                continue
            if handoff_lines:
                fragments[-1].extend(handoff_lines)
        if fragments[-1] and _starts_new_fragment(line, fragments[-1]):
            fragments.append([line])
            continue
        fragments[-1].append(line)
    return ["\n".join(fragment).strip() for fragment in fragments if any(line.strip() for line in fragment)]


def _starts_new_fragment(line: str, current_fragment: list[str]) -> bool:
    normalized = _normalize_text(line)
    if "tem agora a palavra, para uma declaracao politica" in normalized:
        return True
    if normalized.startswith("declaracao politica do "):
        return True
    return False


def _speaker_line_starts_new_fragment(line: str, current_fragment: list[str]) -> bool:
    if not current_fragment:
        return False
    if not _speaker_heading_match(line):
        return False
    return _fragment_ends_with_handoff(current_fragment)


def _fragment_ends_with_handoff(fragment: list[str]) -> bool:
    tail = fragment[-2:] if len(fragment) > 1 else fragment
    return any(_is_handoff_line(line) for line in tail)


def _extract_trailing_handoff_lines(fragment: list[str]) -> list[str]:
    collected: list[str] = []
    while fragment and _is_handoff_line(fragment[-1]):
        collected.insert(0, fragment.pop())
    return collected


def _is_handoff_line(line: str) -> bool:
    normalized = _normalize_text(line)
    return any(
        marker in normalized
        for marker in (
            "tem a palavra",
            "tem agora a palavra",
            "para o primeiro pedido de esclarecimento",
            "para um segundo pedido de esclarecimento",
            "para um pedido de esclarecimento",
            "para responder",
            "faca favor",
        )
    )


def _classify_heading(heading: str, markdown: str) -> tuple[str, str]:
    upper_heading = heading.upper()
    upper_markdown = markdown.upper()
    handoff_speaker = _speaker_after_president_handoff(markdown)
    if handoff_speaker is not None:
        speaker_name, party = handoff_speaker
        normalized_heading = _normalize_text(markdown.splitlines()[0])
        if "declaracao politica" in normalized_heading:
            return f"declaracao-politica-{speaker_name}-{party}", "political_declaration"
        return f"speech-{speaker_name}-{party}", "speech"

    speaker_match = _speaker_heading_match(heading)

    if "SUMÁRIO" in upper_heading or "SUMARIO" in upper_heading:
        return "Session summary", "session_summary"
    if "EM DECLARAÇÃO POLÍTICA" in upper_markdown or "EM DECLARACAO POLITICA" in upper_markdown:
        return "Session summary", "session_summary"
    if "VOTAÇÃO" in upper_heading or "VOTACAO" in upper_heading:
        return "Vote", "vote"
    if (
        "TEM AGORA A PALAVRA, PARA UMA DECLARAÇÃO POLÍTICA" in upper_markdown
        or "TEM AGORA A PALAVRA, PARA UMA DECLARACAO POLITICA" in upper_markdown
    ):
        party_match = re.search(
            r"SR\.?\s+DEPUTAD[OA]\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç\s]+)\s*\(([^)]+)\)",
            markdown,
            re.IGNORECASE,
        )
        if party_match:
            speaker_name = party_match.group(1).strip().lower()
            party = party_match.group(2).strip().lower()
            return f"declaracao-politica-{speaker_name}-{party}", "political_declaration"
        return "Declaracao politica", "political_declaration"
    if "DECLARAÇÃO POLÍTICA" in upper_heading or "DECLARACAO POLITICA" in upper_heading:
        party_match = re.search(
            r"DECLARA(?:ÇÃO|CAO)\s+POL[ÍI]TICA\s+DO\s+([A-ZÇÉÍÓÚÂÊÔÃÕ-]+)",
            upper_heading,
        )
        party = party_match.group(1) if party_match else "PARTIDO"
        return f"Declaracao politica do {party.lower()}", "political_declaration"
    if "SESSÃO SOLENE" in upper_markdown or "SESSAO SOLENE" in upper_markdown:
        return "Sessao solene", "solemn_session"
    if (
        re.search(r"(^|\n)_?ERAM\s+\d{1,2}\s+HORAS", upper_markdown)
        and "ESTÁ ABERTA A SESSÃO" not in upper_markdown
        and "SESSÃO SOLENE" not in upper_markdown
        and "VERKHOVNA RADA" not in upper_markdown
    ):
        return "Closing notes", "closing_notes"
    if "VERKHOVNA RADA" in upper_markdown or "SLAVA UKRAINI" in upper_markdown:
        return "Sessao solene", "solemn_session"
    if speaker_match:
        speaker_name = speaker_match.group(1).strip().lower()
        party = speaker_match.group(2).strip().lower()
        return f"speech-{speaker_name}-{party}", "speech"
    return heading.title(), "debate"


def _split_section(section: Section, max_section_chars: int) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in section.text.split("\n") if paragraph.strip()]
    parts: list[str] = []
    current: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        extra = len(paragraph) + (1 if current else 0)
        if current and current_length + extra > max_section_chars:
            parts.append("\n".join(current))
            current = [paragraph]
            current_length = len(paragraph)
            continue
        current.append(paragraph)
        current_length += extra

    if current:
        parts.append("\n".join(current))

    if not parts:
        return [section.text]
    return parts


def _part_suffixes(count: int) -> list[str]:
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    if count <= len(alphabet):
        return list(alphabet[:count])
    return [f"{math.floor(index / len(alphabet))}{alphabet[index % len(alphabet)]}" for index in range(count)]


def _strip_page_furniture(markdown: str) -> str:
    lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    cleaned: list[str] = []
    for line in lines:
        upper_line = line.upper().replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
        if upper_line.startswith("**I SERIE") or upper_line.startswith("**I SÉRIE"):
            continue
        if re.fullmatch(r"\**\d+\**", line):
            continue
        if "LEGISLATURA" in upper_line or "SESSAO LEGISLATIVA" in upper_line or "SESSÃO LEGISLATIVA" in upper_line:
            continue
        if re.fullmatch(r"\**\d{1,2}\s+DE\s+[A-ZÇÉÍÓÚÂÊÔÃÕa-zçéíóúâêôãõ]+\s+DE\s+\d{4}\**", line):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def _normalize_text(text: str) -> str:
    upper = text.lower()
    replacements = str.maketrans(
        {
            "á": "a",
            "à": "a",
            "â": "a",
            "ã": "a",
            "é": "e",
            "ê": "e",
            "í": "i",
            "ó": "o",
            "ô": "o",
            "õ": "o",
            "ú": "u",
            "ç": "c",
        }
    )
    return upper.translate(replacements)


def _merge_adjacent_sections(sections: list[Section]) -> list[Section]:
    if not sections:
        return []

    merged = [sections[0]]
    for section in sections[1:]:
        previous = merged[-1]
        if _should_merge_as_continuation(previous, section):
            merged[-1] = Section(
                document_id=previous.document_id,
                section_id="",
                title=previous.title,
                section_type=previous.section_type,
                start_page=previous.start_page,
                end_page=section.end_page,
                text=f"{previous.text}\n\n{section.text}".strip(),
                source_pages=previous.source_pages + section.source_pages,
            )
            continue
        if previous.section_type == section.section_type and previous.title == section.title:
            merged[-1] = Section(
                document_id=previous.document_id,
                section_id="",
                title=previous.title,
                section_type=previous.section_type,
                start_page=previous.start_page,
                end_page=section.end_page,
                text=f"{previous.text}\n\n{section.text}".strip(),
                source_pages=previous.source_pages + section.source_pages,
            )
            continue
        merged.append(section)
    return merged


def _should_merge_as_continuation(previous: Section, current: Section) -> bool:
    if previous.section_type not in {"solemn_session", "speech", "political_declaration", "debate"}:
        return False
    if current.section_type not in {"debate", "closing_notes"}:
        return False
    if _starts_with_explicit_new_section_marker(current.text):
        return False
    return True


def _starts_with_explicit_new_section_marker(text: str) -> bool:
    first_line = _first_content_line(text)
    if not first_line:
        return False
    upper = first_line.upper()
    return (
        "SUMÁRIO" in upper
        or "SUMARIO" in upper
        or "VOTAÇÃO" in upper
        or "VOTACAO" in upper
        or "DECLARAÇÃO POLÍTICA" in upper
        or "DECLARACAO POLITICA" in upper
        or "SESSÃO SOLENE" in upper
        or "SESSAO SOLENE" in upper
        or _speaker_heading_match(first_line) is not None
    )


def _looks_like_continuation(text: str) -> bool:
    first_line = _first_content_line(text)
    if not first_line:
        return False
    normalized = _normalize_text(first_line).lstrip("#*_ -")
    if not normalized:
        return False
    if first_line[:1].islower():
        return True
    return normalized.startswith(
        (
            "aplausos",
            "protestos",
            "continuacao",
            "continuação",
            "burburinho",
            "riso",
            "risos",
            "portanto",
            "e ",
            "mas ",
        )
    )


def _first_content_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _speaker_heading_match(line: str) -> re.Match[str] | None:
    match = re.match(
        r"^(?:O|A)\s+Sr\.?ª?\s+\*\*([^*]+)\*\*\s+\(([^)]+)\)",
        line,
        re.IGNORECASE,
    )
    if match:
        return match
    return re.match(
        r"^(?:O|A)\s+Sr\.?ª?\s+(?:Deputad[oa]\s+)?([^:(]+?)\s+\(([^)]+)\)",
        line,
        re.IGNORECASE,
    )


def _speaker_after_president_handoff(markdown: str) -> tuple[str, str] | None:
    lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    first_line = lines[0]
    if "presidente" not in _normalize_text(first_line) or not _is_handoff_line(first_line):
        return None
    for line in lines[1:]:
        match = _speaker_heading_match(line)
        if match is None:
            continue
        speaker_name = match.group(1).strip().lower()
        if speaker_name == "presidente":
            continue
        party = match.group(2).strip().lower()
        return speaker_name, party
    return None
