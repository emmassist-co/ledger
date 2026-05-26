from __future__ import annotations

import re
from pathlib import Path

import yaml

from ledger.models.artifacts import ArtifactLink, EpisodeNote, GenerationSummary


def read_episode_note(path: Path) -> EpisodeNote:
    raw = path.read_text()
    frontmatter, body = _split_frontmatter(raw)
    metadata = yaml.safe_load(frontmatter) or {}
    sections = _parse_body_sections(body)
    return EpisodeNote(
        document_id=metadata["document_id"],
        episode_id=metadata["episode_id"],
        title=metadata["title"],
        episode_type=metadata["type"],
        pages=list(metadata.get("pages", [])),
        topics=list(metadata.get("topics", [])),
        actors=list(metadata.get("actors", [])),
        parties=list(metadata.get("parties", [])),
        importance=metadata.get("importance", "medium"),
        references=[_read_link(item) for item in metadata.get("references", [])],
        claims=[_read_link(item) for item in metadata.get("claims", [])],
        generation=_read_generation(metadata.get("generation")),
        what_happened=sections.get("What happened", ""),
        why_it_mattered=sections.get("Why it mattered", ""),
        main_actors=sections.get("Main actors", ""),
        party_positions=sections.get("Party positions or reactions", ""),
        important_claims=sections.get("Important claims", ""),
        external_references_to_check=sections.get("External references to check", ""),
        evidence_pointers=_parse_evidence_pointers(sections.get("Evidence pointers", "")),
    )


def _split_frontmatter(raw: str) -> tuple[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.DOTALL)
    if not match:
        raise ValueError("Invalid markdown artifact frontmatter")
    return match.group(1), match.group(2)


def _parse_body_sections(body: str) -> dict[str, str]:
    parts = re.split(r"^##\s+", body, flags=re.MULTILINE)
    parsed: dict[str, str] = {}
    for part in parts[1:]:
        lines = part.splitlines()
        if not lines:
            continue
        heading = lines[0].strip()
        content = "\n".join(lines[1:]).strip()
        parsed[heading] = content
    return parsed


def _parse_evidence_pointers(block: str) -> list[str]:
    if not block.strip():
        return []
    pointers: list[str] = []
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        if stripped:
            pointers.append(stripped)
    return pointers


def _read_link(payload: dict[str, object]) -> ArtifactLink:
    return ArtifactLink(
        id=str(payload["id"]),
        type=str(payload["type"]),
        path=str(payload["path"]),
        relationship=str(payload["relationship"]) if payload.get("relationship") else None,
        anchor=str(payload["anchor"]) if payload.get("anchor") else None,
    )


def _read_generation(payload: dict[str, object] | None) -> GenerationSummary | None:
    if not payload:
        return None
    return GenerationSummary(
        event_id=str(payload["event_id"]),
        model=str(payload["model"]),
        prompt_template=str(payload["prompt_template"]),
        input_tokens=int(payload.get("input_tokens", 0)),
        output_tokens=int(payload.get("output_tokens", 0)),
        estimated_cost_usd=float(payload.get("estimated_cost_usd", 0.0)),
    )
