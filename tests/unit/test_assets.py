from __future__ import annotations

from pathlib import Path

from parliament.config import load_config


def test_repo_local_skills_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    expected = [
        "skills/process-parliamentary-transcript/SKILL.md",
        "skills/pdf-parser/SKILL.md",
        "skills/section-detector/SKILL.md",
        "skills/section-note-writer/SKILL.md",
        "skills/claims-and-references-extractor/SKILL.md",
        "skills/complexity-slider-renderer/SKILL.md",
    ]

    for relative_path in expected:
        assert (root / relative_path).exists(), relative_path


def test_sample_config_loads() -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_config(root / "config" / "models.example.yaml")

    assert config.models.section_note


def test_readme_mentions_process_command() -> None:
    root = Path(__file__).resolve().parents[2]
    readme = (root / "README.md").read_text()

    assert "parliament process" in readme
