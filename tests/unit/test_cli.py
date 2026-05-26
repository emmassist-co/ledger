from __future__ import annotations

from pathlib import Path

from ledger.cli import _rollup_costs, build_parser
from ledger.config import AppConfig, load_config, load_dotenv_file
from ledger.io.paths import DocumentPaths


def test_build_parser_exposes_process_command() -> None:
    parser = build_parser()

    namespace = parser.parse_args(["process", "document.pdf", "--resume", "--start-section", "2", "--max-sections", "5"])

    assert namespace.command == "process"
    assert namespace.pdf_path == "document.pdf"
    assert namespace.resume is True
    assert namespace.start_section == 2
    assert namespace.max_sections == 5


def test_build_parser_exposes_archive_rebuild_index_command() -> None:
    parser = build_parser()

    namespace = parser.parse_args(["archive", "rebuild-index", "--root", "archive-index"])

    assert namespace.command == "archive"
    assert namespace.archive_command == "rebuild-index"
    assert namespace.root == Path("archive-index")


def test_build_parser_exposes_archive_dr_build_commands() -> None:
    parser = build_parser()

    outer_map = parser.parse_args(["archive", "build-dr-outer-map", "--root", "archive-index", "--window", "recent"])
    tax_vertical = parser.parse_args(
        ["archive", "build-dr-tax-vertical", "--root", "archive-index", "--anchor", "irc"]
    )

    assert outer_map.command == "archive"
    assert outer_map.archive_command == "build-dr-outer-map"
    assert outer_map.window == "recent"
    assert tax_vertical.archive_command == "build-dr-tax-vertical"
    assert tax_vertical.anchor == "irc"


def test_load_config_returns_defaults_when_file_missing() -> None:
    config = load_config(None)

    assert isinstance(config, AppConfig)
    assert config.models.section_note
    assert config.models.index
    assert config.pipeline.max_section_chars > 0


def test_load_config_reads_yaml_file(tmp_path: Path) -> None:
    config_path = tmp_path / "models.yaml"
    config_path.write_text(
        """
models:
  section_note: openrouter/test-note
  claims: openrouter/test-claims
  index: openrouter/test-index
  level_1: openrouter/test-level-1
  level_2: openrouter/test-level-2
  level_3: openrouter/test-level-3
pipeline:
  output_root: custom-documents
  max_section_chars: 3210
  enable_resolver: false
""".strip()
    )

    config = load_config(config_path)

    assert config.models.section_note == "openrouter/test-note"
    assert config.models.claims == "openrouter/test-claims"
    assert config.models.index == "openrouter/test-index"
    assert config.pipeline.output_root == "custom-documents"
    assert config.pipeline.max_section_chars == 3210


def test_load_dotenv_file_sets_environment_variables(tmp_path: Path, monkeypatch) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "OPENROUTER_API_KEY=test-openrouter-key\nLEDGER_FAKE_LLM_OUTPUT=Texto fake\n"
    )
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("LEDGER_FAKE_LLM_OUTPUT", raising=False)

    load_dotenv_file(dotenv_path)

    import os

    assert os.getenv("OPENROUTER_API_KEY") == "test-openrouter-key"
    assert os.getenv("LEDGER_FAKE_LLM_OUTPUT") == "Texto fake"


def test_rollup_costs_counts_batch_generation_once(tmp_path: Path) -> None:
    paths = DocumentPaths.from_root(tmp_path, "DAR-I-TEST")
    paths.runs_dir.mkdir(parents=True, exist_ok=True)
    (paths.runs_dir / "events.jsonl").write_text(
        "\n".join(
            [
                '{"artifact_type":"episode","estimated_cost_usd":0.01}',
                '{"artifact_type":"claims_and_references","estimated_cost_usd":0.02}',
                '{"artifact_type":"view","estimated_cost_usd":0.03}',
            ]
        )
        + "\n"
    )

    summary = _rollup_costs(paths)

    assert summary["total_estimated_cost_usd"] == 0.06
    assert summary["by_artifact_type"]["claims_and_references"] == 0.02
