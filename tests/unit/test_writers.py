from __future__ import annotations

import json
from pathlib import Path

from ledger.io.paths import DocumentPaths
from ledger.io.writers import (
    append_generation_event,
    write_episode_note,
    write_metadata,
    write_view_artifact,
)
from ledger.models.artifacts import ArtifactLink, EpisodeNote, GenerationEvent, GenerationSummary, ViewArtifact


def test_document_paths_build_expected_locations(tmp_path: Path) -> None:
    paths = DocumentPaths.from_root(tmp_path, "DAR-I-TEST")

    assert paths.document_root == tmp_path / "DAR-I-TEST"
    assert paths.episodes_dir == tmp_path / "DAR-I-TEST" / "episodes"
    assert paths.claims_dir == tmp_path / "DAR-I-TEST" / "claims"
    assert paths.runs_dir == tmp_path / "DAR-I-TEST" / "runs"


def test_write_episode_note_renders_frontmatter_and_body(tmp_path: Path) -> None:
    paths = DocumentPaths.from_root(tmp_path, "DAR-I-TEST")
    note = EpisodeNote(
        document_id="DAR-I-TEST",
        episode_id="ep-0001-pcp-labour",
        title="PCP labour cost of living",
        episode_type="declaration_block",
        pages=[2, 3],
        topics=["trabalho", "desigualdade"],
        actors=["Paula Santos"],
        parties=["PCP"],
        importance="high",
        references=[
            ArtifactLink(id="ref-0001-oecd", type="reference", path="../references/ref-0001-oecd.md")
        ],
        generation=GenerationSummary(
            event_id="gen-episode-1",
            model="openai/gpt-4.1-mini",
            prompt_template="episode-note@v1",
            input_tokens=100,
            output_tokens=50,
            estimated_cost_usd=0.001,
        ),
        what_happened="Houve uma declaração política.",
        why_it_mattered="Introduziu conflito político.",
        main_actors="Paula Santos liderou a intervenção.",
        party_positions="O PCP criticou o custo de vida.",
        important_claims="Paula Santos afirmou que a desigualdade aumentou.",
        external_references_to_check="Comissão Europeia sobre desigualdade.",
        evidence_pointers=["Page 2: abertura da declaração."],
    )

    note_path = write_episode_note(paths, note)
    content = note_path.read_text()

    assert content.startswith("---\n")
    assert "episode_id: ep-0001-pcp-labour" in content
    assert "artifact_type: episode" in content
    assert "## What happened" in content
    assert "Page 2: abertura da declaração." in content


def test_write_view_artifact_renders_frontmatter_and_body(tmp_path: Path) -> None:
    paths = DocumentPaths.from_root(tmp_path, "DAR-I-TEST")
    view = ViewArtifact(
        document_id="DAR-I-TEST",
        view_id="level-1-simple",
        level=1,
        title="O que aconteceu no Parlamento",
        markdown="# Título\n\nTexto",
        source_episodes=[ArtifactLink(id="ep-0001", type="episode", path="../episodes/ep-0001.md")],
    )

    view_path = write_view_artifact(paths, view)

    assert "view_id: level-1-simple" in view_path.read_text()
    assert "# Título" in view_path.read_text()


def test_append_generation_event_persists_jsonl(tmp_path: Path) -> None:
    paths = DocumentPaths.from_root(tmp_path, "DAR-I-TEST")
    event = GenerationEvent(
        event_id="gen-1",
        document_id="DAR-I-TEST",
        artifact_type="episode",
        artifact_id="ep-0001",
        model="openai/gpt-4.1-mini",
        prompt_template="episode-note@v1",
        input_tokens=100,
        output_tokens=50,
        estimated_cost_usd=0.001,
        status="success",
    )

    log_path = append_generation_event(paths, event)

    line = json.loads(log_path.read_text().strip())
    assert line["event_id"] == "gen-1"


def test_write_metadata_persists_json(tmp_path: Path) -> None:
    paths = DocumentPaths.from_root(tmp_path, "DAR-I-TEST")

    metadata_path = write_metadata(paths, {"document_id": "DAR-I-TEST", "page_count": 3})

    loaded = json.loads(metadata_path.read_text())
    assert loaded["page_count"] == 3
