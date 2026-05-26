from __future__ import annotations

from pathlib import Path

from ledger.archive_index.artifacts import read_archive_artifact, write_archive_artifact


def test_write_and_read_archive_artifact_round_trips_frontmatter_and_body(tmp_path: Path) -> None:
    path = tmp_path / "archive-index" / "artifacts" / "dr" / "registry" / "reg-dr-lei-13-2023.md"

    written_path = write_archive_artifact(
        path=path,
        frontmatter={
            "artifact_type": "registry",
            "artifact_id": "reg-dr-lei-13-2023",
            "source_system": "diariodarepublica.pt",
            "source_url": "https://diariodarepublica.pt/dr/detalhe/parlamento/13-2023-211340863",
            "linked_ids": ["ent-agenda-do-trabalho-digno"],
            "confidence": "high",
            "optional_field": None,
        },
        body="# Lei n.º 13/2023\n\nTexto de teste.\n",
    )

    artifact = read_archive_artifact(written_path)

    assert written_path == path
    assert artifact.metadata["artifact_type"] == "registry"
    assert artifact.metadata["artifact_id"] == "reg-dr-lei-13-2023"
    assert artifact.metadata["linked_ids"] == ["ent-agenda-do-trabalho-digno"]
    assert "optional_field" not in artifact.metadata
    assert artifact.body == "# Lei n.º 13/2023\n\nTexto de teste.\n"


def test_read_archive_artifact_supports_multiple_dr_types(tmp_path: Path) -> None:
    path = tmp_path / "archive-index" / "artifacts" / "dr" / "consolidation-notes" / "note-irc-capital-gains.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """---
artifact_type: consolidation_note
artifact_id: note-irc-capital-gains
linked_ids:
  - act-irc
  - art-irc-46
  - rel-irc-ebf-participation
confidence: medium
---

# Capital gains note

Current operative rule.
"""
    )

    artifact = read_archive_artifact(path)

    assert artifact.metadata["artifact_type"] == "consolidation_note"
    assert artifact.metadata["linked_ids"] == ["act-irc", "art-irc-46", "rel-irc-ebf-participation"]
    assert "Current operative rule." in artifact.body
