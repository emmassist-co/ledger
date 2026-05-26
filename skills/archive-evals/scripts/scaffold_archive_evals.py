from __future__ import annotations

import json
import sys
from pathlib import Path


MANIFEST = {
    "schema_version": 1,
    "archive_evals_version": 1,
    "buckets": ["retrieval", "grounding", "boundary"],
    "defaults": {
        "scenario_count_target": 6,
        "corpus_derived_target": 3,
        "user_seeded_target": 3,
    },
}


README = """# Archive Evals Workspace

This workspace stores eval scenarios and reports for an archive created with `archive-index-builder`.

Start with:

- `manifest.json`
- `scenarios/`
- `reports/`

Use the companion runner in:

- `skills/archive-evals/scripts/run_archive_evals.py`
"""


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def scaffold(root: Path) -> None:
    evals_root = root / "archive-evals"
    for relative in ("scenarios", "reports", "runs"):
        (evals_root / relative).mkdir(parents=True, exist_ok=True)
    write_json(evals_root / "manifest.json", MANIFEST)
    write_text(evals_root / "README.md", README)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: scaffold_archive_evals.py ARCHIVE_ROOT", file=sys.stderr)
        return 2
    scaffold(Path(argv[1]).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
