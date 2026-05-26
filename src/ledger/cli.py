from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from ledger.archive_index.navigation import rebuild_navigation_index
from ledger.archive_index.paths import ArchiveIndexPaths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ledger")
    subparsers = parser.add_subparsers(dest="command", required=True)

    archive_parser = subparsers.add_parser("archive", help="Archive workspace operations")
    archive_subparsers = archive_parser.add_subparsers(dest="archive_command", required=True)

    scaffold_parser = archive_subparsers.add_parser("scaffold", help="Scaffold a new archive workspace")
    scaffold_parser.add_argument("root", type=Path)

    rebuild_parser = archive_subparsers.add_parser("rebuild-index", help="Rebuild an archive navigation index")
    rebuild_parser.add_argument("--root", type=Path, required=True)

    verify_parser = archive_subparsers.add_parser("verify", help="Run an archive workspace verifier check")
    verify_parser.add_argument("--root", type=Path, required=True)
    verify_parser.add_argument("check")
    verify_parser.add_argument("extra_args", nargs=argparse.REMAINDER)

    eval_parser = subparsers.add_parser("eval", help="Archive eval operations")
    eval_subparsers = eval_parser.add_subparsers(dest="eval_command", required=True)

    eval_scaffold_parser = eval_subparsers.add_parser("scaffold", help="Scaffold archive eval files")
    eval_scaffold_parser.add_argument("archive_root", type=Path)

    eval_generate_parser = eval_subparsers.add_parser(
        "generate-corpus", help="Generate a small corpus-derived eval scenario set"
    )
    eval_generate_parser.add_argument("archive_root", type=Path)
    eval_generate_parser.add_argument("--limit", type=int, default=6)

    eval_run_parser = eval_subparsers.add_parser("run", help="Run archive eval scenarios")
    eval_run_parser.add_argument("archive_root", type=Path)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "archive":
        return _run_archive_command(args, parser)
    if args.command == "eval":
        return _run_eval_command(args)

    parser.error(f"Unsupported command: {args.command}")
    return 2


def _run_archive_command(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.archive_command == "scaffold":
        return _run_repo_script(
            "skills/archive-index-builder/scripts/scaffold_archive_index.py",
            [str(args.root)],
        )
    if args.archive_command == "rebuild-index":
        rebuild_navigation_index(ArchiveIndexPaths(args.root))
        return 0
    if args.archive_command == "verify":
        verifier_path = args.root / "scripts" / "archive_verifier.py"
        extra_args = list(args.extra_args)
        if extra_args[:1] == ["--"]:
            extra_args = extra_args[1:]
        return _run_python_script(verifier_path, [args.check, str(args.root), *extra_args])

    parser.error(f"Unsupported archive command: {args.archive_command}")
    return 2


def _run_eval_command(args: argparse.Namespace) -> int:
    if args.eval_command == "scaffold":
        return _run_repo_script(
            "skills/archive-evals/scripts/scaffold_archive_evals.py",
            [str(args.archive_root)],
        )
    if args.eval_command == "generate-corpus":
        return _run_repo_script(
            "skills/archive-evals/scripts/run_archive_evals.py",
            ["generate-corpus", str(args.archive_root), "--limit", str(args.limit)],
        )
    if args.eval_command == "run":
        return _run_repo_script(
            "skills/archive-evals/scripts/run_archive_evals.py",
            ["run", str(args.archive_root)],
        )
    return 2


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_repo_script(relative_path: str, args: list[str]) -> int:
    return _run_python_script(_repo_root() / relative_path, args)


def _run_python_script(script_path: Path, args: list[str]) -> int:
    completed = subprocess.run([sys.executable, str(script_path), *args], check=False)
    return completed.returncode
