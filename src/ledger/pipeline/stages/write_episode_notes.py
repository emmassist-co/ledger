from __future__ import annotations

import ast

from ledger.llm.json_utils import extract_json_object
from ledger.models.artifacts import EpisodeNote, GenerationSummary
from ledger.models.episode import Episode


def write_episode_notes(episodes: list[Episode], generator) -> list[EpisodeNote]:
    notes: list[EpisodeNote] = []
    for episode in episodes:
        prompt = "\n".join(
            [
                "You are processing one episode of a Portuguese parliamentary transcript.",
                "Return JSON only. Write the content fields in Portuguese.",
                "Rules:",
                "- Distinguish transcript-established facts from speaker claims.",
                "- Do not verify external claims.",
                "- Preserve parties, actors, and evidence pointers.",
                "- Keep evidence pointers short and page-anchored.",
                "- `importance` must be exactly one of: low, medium, high.",
                "",
                f"Episode ID: {episode.episode_id}",
                f"Title: {episode.title}",
                f"Type: {episode.episode_type}",
                f"Pages: {episode.start_page}-{episode.end_page}",
                "",
                "Episode text:",
                episode.text,
                "",
                "Return JSON only with keys:",
                "topics, actors, parties, importance, external_refs, what_happened, why_it_mattered, main_actors, party_positions, important_claims, external_references_to_check, evidence_pointers",
            ]
        )
        result = _generate_result(generator, prompt)
        generated = extract_json_object(result.text)
        notes.append(
            EpisodeNote(
                document_id=episode.document_id,
                episode_id=episode.episode_id,
                title=episode.title,
                episode_type=episode.episode_type,
                pages=[episode.start_page, episode.end_page],
                topics=_coerce_string_list(generated.get("topics", [])),
                actors=_coerce_string_list(generated.get("actors", [])),
                parties=_coerce_string_list(generated.get("parties", [])),
                importance=_coerce_importance(generated.get("importance", "medium")),
                generation=GenerationSummary(
                    event_id="",
                    model=result.model,
                    prompt_template="episode-note@v1",
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    estimated_cost_usd=result.estimated_cost_usd,
                ),
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
                    f"Page {page}: supporting passage in source episode."
                    for page in episode.source_pages
                ],
            )
        )
    return notes


def _generate_result(generator, prompt: str):
    if hasattr(generator, "generate_result"):
        return generator.generate_result(prompt)
    text = generator.generate(prompt)
    return type("Result", (), {"text": text, "model": "static", "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0})()


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
