from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ledger.consultation.runtime import consult_archive


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "ledger", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_archive_lifecycle_commands(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive-index"
    write_jsonl(
        archive_root / "index" / "documents.jsonl",
        [
            {
                "artifact_id": "art-vat",
                "title": "VAT deduction rule",
                "artifact_type": "extract",
                "search_text": "vat deduction rule article input tax deductible",
                "path": str(archive_root / "artifacts" / "extracts" / "art-vat.md"),
            }
        ],
    )
    write_json(archive_root / "artifacts" / "state" / "source-freshness.json", {"schema_version": 1, "families": {}})

    consult_archive(archive_root, "What is the VAT deduction rule?")

    result = run_cli("archive", "summarize-state", "--root", str(archive_root), cwd=Path(__file__).resolve().parents[2])
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["document_count"] == 1

    result = run_cli("archive", "list-consultations", "--root", str(archive_root), cwd=Path(__file__).resolve().parents[2])
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert len(payload["records"]) == 1

    result = run_cli("archive", "prune-consultations", "--root", str(archive_root), "--keep", "0", cwd=Path(__file__).resolve().parents[2])
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["deleted_count"] == 1
    assert payload["summary"]["consultation_audit_count"] == 0
