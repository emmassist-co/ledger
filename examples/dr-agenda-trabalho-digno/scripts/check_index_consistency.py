from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from rebuild_index import collect_artifacts, write_jsonl


ROOT = Path(__file__).resolve().parents[1]


def read_lines(path: Path):
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def main():
    argparse.ArgumentParser().parse_args()
    documents, links = collect_artifacts()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        docs_tmp = tmp / "documents.jsonl"
        links_tmp = tmp / "links.jsonl"
        write_jsonl(docs_tmp, documents)
        write_jsonl(links_tmp, links)
        current_docs = read_lines(ROOT / "index" / "documents.jsonl")
        current_links = read_lines(ROOT / "index" / "links.jsonl")
        expected_docs = read_lines(docs_tmp)
        expected_links = read_lines(links_tmp)
    failures = []
    if current_docs != expected_docs:
        failures.append({"target": "documents.jsonl", "current_lines": len(current_docs), "expected_lines": len(expected_docs)})
    if current_links != expected_links:
        failures.append({"target": "links.jsonl", "current_lines": len(current_links), "expected_lines": len(expected_links)})
    payload = {"ok": not failures, "check": "check_index_consistency", "summary": "index files match rebuild output" if not failures else "index files differ from rebuild output", "failures": failures}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
