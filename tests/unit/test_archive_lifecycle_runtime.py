from __future__ import annotations

import json
from pathlib import Path

from ledger.archive_lifecycle import (
    list_consultation_records,
    prune_consultation_records,
    summarize_archive_state,
)
from ledger.consultation.runtime import consult_archive


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_archive_lifecycle_lists_and_prunes_consultations(tmp_path: Path) -> None:
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

    first = consult_archive(archive_root, "What is the VAT deduction rule?")
    second = consult_archive(archive_root, "What is the current VAT rule?")

    records = list_consultation_records(archive_root)
    assert len(records) == 2
    assert records[-1]["path"] == str(second.audit_path)

    payload = prune_consultation_records(archive_root, keep=1)
    assert payload["ok"] is True
    assert payload["deleted_count"] == 1
    assert payload["kept_count"] == 1
    assert first.audit_path.exists() is False
    assert second.audit_path.exists() is True

    summary = summarize_archive_state(archive_root)
    assert summary["consultation_audit_count"] == 1
    assert summary["latest_consultation_audit_path"] == str(second.audit_path)
