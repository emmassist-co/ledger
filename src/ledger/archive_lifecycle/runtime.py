from __future__ import annotations

from pathlib import Path

from ledger.consultation.runtime import (
    build_archive_state_summary,
    list_consultation_audits,
    load_consultation_audit,
)


def summarize_archive_state(archive_root: Path) -> dict:
    return build_archive_state_summary(archive_root.resolve())


def list_consultation_records(archive_root: Path) -> list[dict]:
    records = []
    for path in list_consultation_audits(archive_root.resolve()):
        payload = load_consultation_audit(path)
        records.append(
            {
                "consultation_id": str(payload.get("consultation_id", "")).strip(),
                "generated_at": str(payload.get("generated_at", "")).strip(),
                "question": str(payload.get("question", "")).strip(),
                "question_shape": str(payload.get("question_shape", "")).strip(),
                "outcome": str(payload.get("outcome", "")).strip(),
                "path": str(path),
            }
        )
    return records


def prune_consultation_records(archive_root: Path, keep: int) -> dict:
    if keep < 0:
        raise ValueError("keep must be zero or greater")
    root = archive_root.resolve()
    paths = list_consultation_audits(root)
    if keep >= len(paths):
        summary = build_archive_state_summary(root)
        return {
            "ok": True,
            "deleted_count": 0,
            "kept_count": len(paths),
            "deleted_paths": [],
            "summary_path": str(root / "artifacts" / "state" / "archive-state-summary.json"),
            "summary": summary,
        }
    deleted_paths = []
    to_delete = paths[: len(paths) - keep] if keep else paths
    for path in to_delete:
        path.unlink(missing_ok=True)
        deleted_paths.append(str(path))
    summary = build_archive_state_summary(root)
    return {
        "ok": True,
        "deleted_count": len(deleted_paths),
        "kept_count": len(paths) - len(deleted_paths),
        "deleted_paths": deleted_paths,
        "summary_path": str(root / "artifacts" / "state" / "archive-state-summary.json"),
        "summary": summary,
    }
