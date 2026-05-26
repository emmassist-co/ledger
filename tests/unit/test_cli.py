from __future__ import annotations

from pathlib import Path

from ledger.cli import build_parser


def test_build_parser_exposes_archive_scaffold_and_rebuild_commands() -> None:
    parser = build_parser()

    scaffold = parser.parse_args(["archive", "scaffold", "archive-index"])
    rebuild = parser.parse_args(["archive", "rebuild-index", "--root", "archive-index"])

    assert scaffold.command == "archive"
    assert scaffold.archive_command == "scaffold"
    assert scaffold.root == Path("archive-index")
    assert rebuild.archive_command == "rebuild-index"
    assert rebuild.root == Path("archive-index")


def test_build_parser_exposes_archive_verify_and_dr_build_commands() -> None:
    parser = build_parser()

    verify = parser.parse_args(
        ["archive", "verify", "--root", "archive-index", "check_policy", "--", "--action", "expand"]
    )
    outer_map = parser.parse_args(["archive", "build-dr-outer-map", "--root", "archive-index", "--max-acts", "5"])
    tax_vertical = parser.parse_args(["archive", "build-dr-tax-vertical", "--root", "archive-index"])

    assert verify.archive_command == "verify"
    assert verify.check == "check_policy"
    assert verify.extra_args == ["--action", "expand"]
    assert outer_map.archive_command == "build-dr-outer-map"
    assert outer_map.max_acts == 5
    assert tax_vertical.archive_command == "build-dr-tax-vertical"
    assert tax_vertical.anchor == "irc"


def test_build_parser_exposes_eval_commands() -> None:
    parser = build_parser()

    scaffold = parser.parse_args(["eval", "scaffold", "archive-index"])
    generate = parser.parse_args(["eval", "generate-corpus", "archive-index", "--limit", "3"])
    run = parser.parse_args(["eval", "run", "archive-index"])

    assert scaffold.command == "eval"
    assert scaffold.eval_command == "scaffold"
    assert scaffold.archive_root == Path("archive-index")
    assert generate.eval_command == "generate-corpus"
    assert generate.limit == 3
    assert run.eval_command == "run"
