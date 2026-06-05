from __future__ import annotations

import argparse
from pathlib import Path

from ledger import cli
from ledger.cli import build_parser


def test_build_parser_exposes_archive_scaffold_and_rebuild_commands() -> None:
    parser = build_parser()

    scaffold = parser.parse_args(["archive", "scaffold", "archive-index"])
    rebuild = parser.parse_args(["archive", "rebuild-index", "--root", "archive-index"])
    rebuild_source_indexes = parser.parse_args(["archive", "rebuild-source-indexes", "--root", "archive-index"])

    assert scaffold.command == "archive"
    assert scaffold.archive_command == "scaffold"
    assert scaffold.root == Path("archive-index")
    assert rebuild.archive_command == "rebuild-index"
    assert rebuild.root == Path("archive-index")
    assert rebuild_source_indexes.archive_command == "rebuild-source-indexes"
    assert rebuild_source_indexes.root == Path("archive-index")


def test_build_parser_exposes_archive_verify_command() -> None:
    parser = build_parser()

    verify = parser.parse_args(
        ["archive", "verify", "--root", "archive-index", "check_policy", "--", "--action", "expand"]
    )

    assert verify.archive_command == "verify"
    assert verify.check == "check_policy"
    assert verify.extra_args == ["--action", "expand"]


def test_build_parser_exposes_eval_commands() -> None:
    parser = build_parser()

    scaffold = parser.parse_args(["eval", "scaffold", "archive-index"])
    generate = parser.parse_args(["eval", "generate-corpus", "archive-index", "--limit", "3"])
    run = parser.parse_args(["eval", "run", "archive-index"])
    summary = parser.parse_args(["eval", "summarize-examples", "examples"])

    assert scaffold.command == "eval"
    assert scaffold.eval_command == "scaffold"
    assert scaffold.archive_root == Path("archive-index")
    assert generate.eval_command == "generate-corpus"
    assert generate.limit == 3
    assert run.eval_command == "run"
    assert summary.eval_command == "summarize-examples"
    assert summary.examples_root == Path("examples")


def test_run_eval_command_scaffolds_repo_local_eval_workspace(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive-index"

    result = cli._run_eval_command(argparse.Namespace(eval_command="scaffold", archive_root=archive_root))

    assert result == 0
    assert (archive_root / "archive-evals" / "manifest.json").exists()
    assert (archive_root / "archive-evals" / "README.md").exists()
    assert (archive_root / "scripts" / "run_archive_evals.py").exists()
    assert (archive_root / "scripts" / "scaffold_archive_evals.py").exists()


def test_run_eval_command_prefers_archive_local_runner(tmp_path: Path, monkeypatch) -> None:
    archive_root = tmp_path / "archive-index"
    local_runner = archive_root / "scripts" / "run_archive_evals.py"
    local_runner.parent.mkdir(parents=True, exist_ok=True)
    local_runner.write_text("print('local')\n", encoding="utf-8")
    calls: list[tuple[Path, list[str]]] = []

    def fake_run_python_script(script_path: Path, args: list[str]) -> int:
        calls.append((script_path, args))
        return 0

    monkeypatch.setattr(cli, "_run_python_script", fake_run_python_script)

    result = cli._run_eval_command(argparse.Namespace(eval_command="run", archive_root=archive_root))

    assert result == 0
    assert calls == [(local_runner, ["run", str(archive_root.resolve())])]
