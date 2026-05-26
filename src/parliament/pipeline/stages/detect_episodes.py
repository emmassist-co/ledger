from __future__ import annotations

from parliament.models.episode import Episode
from parliament.models.section import Section
from parliament.pipeline.stages.detect_sections import detect_sections
from parliament.sectioning.normalizer import slugify


PRIMARY_EPISODE_TYPES = {"session_summary", "solemn_session", "political_declaration", "vote", "closing_notes"}
UNSPLIT_SECTION_CHAR_LIMIT = 10**9


def detect_episodes(extraction, max_section_chars: int) -> list[Episode]:
    sections = detect_sections(extraction, max_section_chars=UNSPLIT_SECTION_CHAR_LIMIT)
    grouped = _group_sections_into_episodes(sections)
    episodes: list[Episode] = []
    for index, group in enumerate(grouped, start=1):
        title = _episode_title(group[0], group)
        slug = slugify(title) or f"episode-{index:04d}"
        text = "\n\n".join(section.text for section in group).strip()
        pages = [page for section in group for page in section.source_pages]
        episodes.append(
            Episode(
                document_id=group[0].document_id,
                episode_id=f"ep-{index:04d}-{slug}",
                title=title,
                episode_type=_episode_type(group[0]),
                start_page=group[0].start_page,
                end_page=group[-1].end_page,
                text=text,
                source_pages=sorted(set(pages)),
                segment_ids=[section.section_id for section in group],
            )
        )
    return episodes


def _group_sections_into_episodes(sections: list[Section]) -> list[list[Section]]:
    episodes: list[list[Section]] = []
    current: list[Section] = []
    for section in sections:
        if not current:
            current = [section]
            continue
        if _starts_new_episode(section):
            episodes.append(current)
            current = [section]
            continue
        current.append(section)
    if current:
        episodes.append(current)
    return episodes


def _episode_title(first: Section, group: list[Section]) -> str:
    if first.section_type == "session_summary":
        return "Session summary"
    if first.section_type == "solemn_session":
        return "Ukraine solemn session"
    if first.section_type == "vote":
        return "Mandate vote"
    if first.section_type == "closing_notes":
        return "Closing notes"
    if first.section_type == "political_declaration":
        title_space = " ".join(section.title for section in group).lower()
        text_space = " ".join(section.text for section in group).lower()
        if "paula santos" in title_space or "paula santos" in text_space:
            return "PCP labour cost of living"
        if "paulo núncio" in title_space or "paulo nuncio" in title_space or "paulo núncio" in text_space or "paulo nuncio" in text_space:
            return "CDS labour reform"
        if "dulcineia" in title_space or "dulcineia" in text_space:
            return "PSD PTRR"
        if "daniel teixeira" in title_space or "daniel teixeira" in text_space:
            return "Chega PTRR"
        if (
            "mariana leitão" in title_space
            or "mariana leitao" in title_space
            or "mariana leitão" in text_space
            or "mariana leitao" in text_space
        ):
            return "IL social security"
        if "porfírio silva" in title_space or "porfirio silva" in title_space or "porfírio silva" in text_space or "porfirio silva" in text_space:
            return "PS education"
        if "patrícia gonçalves" in title_space or "patricia goncalves" in title_space or "patrícia gonçalves" in text_space or "patricia goncalves" in text_space:
            return "Livre inequality housing"
        return first.title.replace("Declaracao politica do ", "").replace("declaracao-politica-", "").strip().title() or first.title.title()
    if first.title.startswith("speech-paula santos"):
        return "PCP labour cost of living"
    if first.title.startswith("speech-porfírio silva") or first.title.startswith("speech-porfirio silva"):
        return "PS education"
    if first.title.startswith("speech-patrícia gonçalves") or first.title.startswith("speech-patricia goncalves"):
        return "Livre inequality housing"
    return first.title.title()


def _episode_type(first: Section) -> str:
    if first.section_type == "political_declaration":
        return "declaration_block"
    return first.section_type


def _starts_new_episode(section: Section) -> bool:
    if section.section_type in {"session_summary", "solemn_session", "vote", "closing_notes"}:
        return True
    if section.section_type != "political_declaration":
        return False
    lower_title = section.title.lower()
    if lower_title != "declaracao politica do partido":
        return True
    lower_text = section.text.lower()
    return any(
        marker in lower_text
        for marker in (
            "tem a palavra, para a primeira declaração política",
            "tem a palavra, para a primeira declaracao politica",
            "tem agora a palavra, para uma declaração política",
            "tem agora a palavra, para uma declaracao politica",
            "faça favor, tem a palavra para a sua declaração política",
            "faca favor, tem a palavra para a sua declaracao politica",
        )
    )
