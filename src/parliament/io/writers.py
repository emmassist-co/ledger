from __future__ import annotations

import json
from pathlib import Path

from parliament.io.paths import DocumentPaths
from parliament.models.artifacts import (
    ClaimArtifact,
    EpisodeNote,
    GenerationEvent,
    ReferenceArtifact,
    ViewArtifact,
)
from parliament.render.frontmatter import render_frontmatter


def write_episode_note(paths: DocumentPaths, note: EpisodeNote) -> Path:
    return _write_markdown_artifact(
        directory=paths.episodes_dir,
        stem=note.episode_id,
        frontmatter={
            "document_id": note.document_id,
            "episode_id": note.episode_id,
            "artifact_type": "episode",
            "title": note.title,
            "type": note.episode_type,
            "pages": note.pages,
            "topics": note.topics,
            "actors": note.actors,
            "parties": note.parties,
            "importance": note.importance,
            "references": [link.to_dict() for link in note.references],
            "claims": [link.to_dict() for link in note.claims],
            "generation": note.generation.to_dict() if note.generation else None,
        },
        body="\n".join(
            [
                f"# {note.title}",
                "",
                "## What happened",
                note.what_happened,
                "",
                "## Why it mattered",
                note.why_it_mattered,
                "",
                "## Main actors",
                note.main_actors,
                "",
                "## Party positions or reactions",
                note.party_positions,
                "",
                "## Important claims",
                note.important_claims,
                "",
                "## External references to check",
                note.external_references_to_check,
                "",
                "## Evidence pointers",
                *[f"- {pointer}" for pointer in note.evidence_pointers],
                "",
            ]
        ),
    )


def write_claim_artifact(paths: DocumentPaths, claim: ClaimArtifact) -> Path:
    return _write_markdown_artifact(
        directory=paths.claims_dir,
        stem=claim.claim_id,
        frontmatter={
            "document_id": claim.document_id,
            "claim_id": claim.claim_id,
            "artifact_type": "claim",
            "title": claim.title,
            "speaker": claim.speaker,
            "party": claim.party,
            "claim_type": claim.claim_type,
            "verification_status": claim.verification_status,
            "priority": claim.priority,
            "episode": claim.episode.to_dict(),
            "references": [link.to_dict() for link in claim.references],
            "generation": claim.generation.to_dict() if claim.generation else None,
        },
        body="\n".join(
            [
                f"# {claim.title}",
                "",
                "## Claim",
                claim.claim,
                "",
                "## Source mention",
                claim.source_mention,
                "",
            ]
        ),
    )


def write_reference_artifact(paths: DocumentPaths, reference: ReferenceArtifact) -> Path:
    return _write_markdown_artifact(
        directory=paths.references_dir,
        stem=reference.reference_id,
        frontmatter={
            "document_id": reference.document_id,
            "reference_id": reference.reference_id,
            "artifact_type": "reference",
            "title": reference.title,
            "name": reference.name,
            "priority": reference.priority,
            "linked_claims": [link.to_dict() for link in reference.linked_claims],
            "linked_episodes": [link.to_dict() for link in reference.linked_episodes],
            "generation": reference.generation.to_dict() if reference.generation else None,
        },
        body="\n".join([f"# {reference.title}", "", reference.description, ""]),
    )


def write_view_artifact(paths: DocumentPaths, view: ViewArtifact) -> Path:
    return _write_markdown_artifact(
        directory=paths.views_dir,
        stem=view.view_id,
        frontmatter={
            "document_id": view.document_id,
            "view_id": view.view_id,
            "artifact_type": "view",
            "level": view.level,
            "title": view.title,
            "source_episodes": [link.to_dict() for link in view.source_episodes],
            "linked_claims": [link.to_dict() for link in view.linked_claims],
            "linked_references": [link.to_dict() for link in view.linked_references],
            "generation": view.generation.to_dict() if view.generation else None,
        },
        body=view.markdown.strip() + "\n",
    )


def append_generation_event(paths: DocumentPaths, event: GenerationEvent) -> Path:
    paths.runs_dir.mkdir(parents=True, exist_ok=True)
    log_path = paths.runs_dir / "events.jsonl"
    with log_path.open("a") as handle:
        handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
    return log_path


def write_metadata(paths: DocumentPaths, metadata: dict[str, object]) -> Path:
    paths.document_root.mkdir(parents=True, exist_ok=True)
    metadata_path = paths.document_root / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    return metadata_path


def write_text_file(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def write_json_file(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return path


def _write_markdown_artifact(
    *,
    directory: Path,
    stem: str,
    frontmatter: dict[str, object],
    body: str,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{stem}.md"
    cleaned_frontmatter = {key: value for key, value in frontmatter.items() if value is not None}
    path.write_text(render_frontmatter(cleaned_frontmatter) + "\n" + body)
    return path
