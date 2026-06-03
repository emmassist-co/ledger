from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from ledger.archive_index.acquisition import fetch_public_webpage
from ledger.archive_index.navigation import rebuild_navigation_index
from ledger.archive_index.paths import ArchiveIndexPaths
from ledger.archive_index.pdf_index import extract_and_index_pdf, index_extracted_pdf, search_pdf_pages
from ledger.archive_index.source_indexes import rebuild_source_indexes
from ledger.archive_index.web_index import search_web_sections


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ledger")
    subparsers = parser.add_subparsers(dest="command", required=True)

    archive_parser = subparsers.add_parser("archive", help="Archive workspace operations")
    archive_subparsers = archive_parser.add_subparsers(dest="archive_command", required=True)

    scaffold_parser = archive_subparsers.add_parser("scaffold", help="Scaffold a new archive workspace")
    scaffold_parser.add_argument("root", type=Path)

    rebuild_parser = archive_subparsers.add_parser("rebuild-index", help="Rebuild an archive navigation index")
    rebuild_parser.add_argument("--root", type=Path, required=True)

    rebuild_source_indexes_parser = archive_subparsers.add_parser(
        "rebuild-source-indexes",
        help="Rebuild source-side PDF and web indexes from stored archive content",
    )
    rebuild_source_indexes_parser.add_argument("--root", type=Path, required=True)

    fetch_parser = archive_subparsers.add_parser(
        "fetch-url", help="Capture a public webpage as Markdown and append a source manifest entry"
    )
    fetch_parser.add_argument("--root", type=Path, required=True)
    fetch_parser.add_argument("--source-id", required=True)
    fetch_parser.add_argument("--url", required=True)
    fetch_parser.add_argument("--source-system")
    fetch_parser.add_argument("--parent-url")
    fetch_parser.add_argument("--download-path", type=Path)
    fetch_parser.add_argument("--method", choices=["auto", "ai", "browser"], default="auto")
    fetch_parser.add_argument("--retain-images", action="store_true")

    search_web_parser = archive_subparsers.add_parser(
        "search-web", help="Search indexed website Markdown sections instead of reading the full page"
    )
    search_web_parser.add_argument("--root", type=Path, required=True)
    search_web_parser.add_argument("--query", required=True)
    search_web_parser.add_argument("--source-id")
    search_web_parser.add_argument("--limit", type=int, default=10)
    search_web_parser.add_argument("--json", action="store_true")

    index_pdf_parser = archive_subparsers.add_parser(
        "index-pdf", help="Extract a PDF into per-page Markdown and build a searchable page index"
    )
    index_pdf_parser.add_argument("--root", type=Path, required=True)
    index_pdf_parser.add_argument("--source-id", required=True)
    index_pdf_parser.add_argument("--pdf-path", type=Path, required=True)
    index_pdf_parser.add_argument("--source-url", default="")
    index_pdf_parser.add_argument("--title", default="")
    index_pdf_parser.add_argument("--extracted-markdown-path", type=Path)

    reindex_pdf_parser = archive_subparsers.add_parser(
        "reindex-pdf", help="Build or rebuild the searchable page index from an extracted PDF Markdown file"
    )
    reindex_pdf_parser.add_argument("--root", type=Path, required=True)
    reindex_pdf_parser.add_argument("--source-id", required=True)
    reindex_pdf_parser.add_argument("--extracted-markdown-path", type=Path, required=True)
    reindex_pdf_parser.add_argument("--source-url", default="")
    reindex_pdf_parser.add_argument("--raw-pdf-path", type=Path)
    reindex_pdf_parser.add_argument("--title", default="")

    search_pdf_parser = archive_subparsers.add_parser(
        "search-pdf", help="Search the per-page PDF index instead of opening full PDFs"
    )
    search_pdf_parser.add_argument("--root", type=Path, required=True)
    search_pdf_parser.add_argument("--query", required=True)
    search_pdf_parser.add_argument("--source-id")
    search_pdf_parser.add_argument("--limit", type=int, default=10)
    search_pdf_parser.add_argument("--json", action="store_true")

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

    eval_summary_parser = eval_subparsers.add_parser(
        "summarize-examples", help="Generate a repo-level benchmark summary from committed examples"
    )
    eval_summary_parser.add_argument("examples_root", type=Path)

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
    if args.archive_command == "rebuild-source-indexes":
        result = rebuild_source_indexes(args.root)
        print(
            json.dumps(
                {
                    "ok": True,
                    "summary": "rebuilt local source indexes",
                    "pdf_sources": result.pdf_sources,
                    "web_sources": result.web_sources,
                    "pdf_index_sqlite": str(result.pdf_index_sqlite),
                    "web_index_sqlite": str(result.web_index_sqlite),
                },
                ensure_ascii=False,
            )
        )
        return 0
    if args.archive_command == "fetch-url":
        result = fetch_public_webpage(
            root=args.root,
            source_id=args.source_id,
            source_url=args.url,
            source_system=args.source_system,
            source_parent_url=args.parent_url,
            download_path=args.download_path,
            markdown_new_method=args.method,
            retain_images=args.retain_images,
        )
        print(
            json.dumps(
                {
                    "ok": True,
                    "source_id": result.source_id,
                    "source_url": result.source_url,
                    "provider": result.provider,
                    "provider_detail": result.provider_detail,
                    "local_path": str(result.local_path),
                    "manifest_path": str(result.manifest_path),
                    "sha256": f"sha256:{result.sha256_hex}",
                    "markdown_tokens": result.markdown_tokens,
                    "fetched_at": result.fetched_at,
                    "web_section_count": result.web_index_result.section_count if result.web_index_result else None,
                    "web_sections_jsonl_path": str(result.web_index_result.sections_jsonl_path)
                    if result.web_index_result
                    else None,
                    "web_sections_sqlite_path": str(result.web_index_result.sqlite_path)
                    if result.web_index_result
                    else None,
                },
                ensure_ascii=False,
            )
        )
        return 0
    if args.archive_command == "search-web":
        hits = search_web_sections(
            root=args.root,
            query=args.query,
            source_id=args.source_id,
            limit=args.limit,
        )
        payload = [
            {
                "source_id": hit.source_id,
                "section_id": hit.section_id,
                "title": hit.title,
                "heading": hit.heading,
                "source_url": hit.source_url,
                "markdown_path": hit.markdown_path,
                "snippet": hit.snippet,
                "rank": hit.rank,
            }
            for hit in hits
        ]
        if args.json:
            print(json.dumps(payload, ensure_ascii=False))
        else:
            print(json.dumps({"ok": True, "results": payload}, ensure_ascii=False))
        return 0
    if args.archive_command == "index-pdf":
        result = extract_and_index_pdf(
            root=args.root,
            source_id=args.source_id,
            pdf_path=args.pdf_path,
            source_url=args.source_url,
            title=args.title,
            extracted_markdown_path=args.extracted_markdown_path,
        )
        print(
            json.dumps(
                {
                    "ok": True,
                    "source_id": result.source_id,
                    "page_count": result.page_count,
                    "extracted_markdown_path": str(result.extracted_markdown_path),
                    "extracted_json_path": str(result.extracted_json_path) if result.extracted_json_path else None,
                    "pages_jsonl_path": str(result.pages_jsonl_path),
                    "sqlite_path": str(result.sqlite_path),
                },
                ensure_ascii=False,
            )
        )
        return 0
    if args.archive_command == "reindex-pdf":
        result = index_extracted_pdf(
            root=args.root,
            source_id=args.source_id,
            extracted_markdown_path=args.extracted_markdown_path,
            source_url=args.source_url,
            raw_pdf_path=args.raw_pdf_path,
            title=args.title,
        )
        print(
            json.dumps(
                {
                    "ok": True,
                    "source_id": result.source_id,
                    "page_count": result.page_count,
                    "extracted_markdown_path": str(result.extracted_markdown_path),
                    "extracted_json_path": str(result.extracted_json_path) if result.extracted_json_path else None,
                    "pages_jsonl_path": str(result.pages_jsonl_path),
                    "sqlite_path": str(result.sqlite_path),
                },
                ensure_ascii=False,
            )
        )
        return 0
    if args.archive_command == "search-pdf":
        hits = search_pdf_pages(
            root=args.root,
            query=args.query,
            source_id=args.source_id,
            limit=args.limit,
        )
        payload = [
            {
                "source_id": hit.source_id,
                "page_number": hit.page_number,
                "title": hit.title,
                "source_url": hit.source_url,
                "raw_pdf_path": hit.raw_pdf_path,
                "extracted_markdown_path": hit.extracted_markdown_path,
                "snippet": hit.snippet,
                "rank": hit.rank,
            }
            for hit in hits
        ]
        if args.json:
            print(json.dumps(payload, ensure_ascii=False))
        else:
            print(json.dumps({"ok": True, "results": payload}, ensure_ascii=False))
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
    if args.eval_command == "summarize-examples":
        return _run_repo_script(
            "skills/archive-evals/scripts/run_archive_evals.py",
            ["summarize-examples", str(args.examples_root)],
        )
    return 2


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_repo_script(relative_path: str, args: list[str]) -> int:
    return _run_python_script(_repo_root() / relative_path, args)


def _run_python_script(script_path: Path, args: list[str]) -> int:
    completed = subprocess.run([sys.executable, str(script_path), *args], check=False)
    return completed.returncode
