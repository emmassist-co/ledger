from __future__ import annotations

from pathlib import Path

from ledger.archive_index.artifacts import read_archive_artifact, write_archive_artifact


def test_write_and_read_archive_artifact_round_trips_frontmatter_and_body(tmp_path: Path) -> None:
    path = tmp_path / "archive-index" / "artifacts" / "beta" / "registry" / "reg-beta-2023.md"

    written_path = write_archive_artifact(
        path=path,
        frontmatter={
            "artifact_type": "registry",
            "artifact_id": "reg-beta-2023",
            "source_system": "example.org",
            "source_url": "https://example.org/beta/2023",
            "linked_ids": ["topic-core-rules"],
            "confidence": "high",
            "optional_field": None,
        },
        body="# Beta Registry 2023\n\nBody text.\n",
    )

    artifact = read_archive_artifact(written_path)

    assert written_path == path
    assert artifact.metadata["artifact_type"] == "registry"
    assert artifact.metadata["artifact_id"] == "reg-beta-2023"
    assert artifact.metadata["linked_ids"] == ["topic-core-rules"]
    assert "optional_field" not in artifact.metadata
    assert artifact.body == "# Beta Registry 2023\n\nBody text.\n"


def test_read_archive_artifact_supports_multiple_artifact_types(tmp_path: Path) -> None:
    path = tmp_path / "archive-index" / "artifacts" / "beta" / "consolidation-notes" / "note-beta-core.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """---
artifact_type: consolidation_note
artifact_id: note-beta-core
linked_ids:
  - act-beta
  - art-beta-46
  - rel-beta-core
confidence: medium
---

# Core note

Current operative rule.
"""
    )

    artifact = read_archive_artifact(path)

    assert artifact.metadata["artifact_type"] == "consolidation_note"
    assert artifact.metadata["linked_ids"] == ["act-beta", "art-beta-46", "rel-beta-core"]
    assert "Current operative rule." in artifact.body
