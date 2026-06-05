from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_archive_index_skill_scaffold_creates_expected_files(tmp_path: Path) -> None:
    script = (
        Path(__file__).resolve().parents[2]
        / "skills"
        / "archive-index-builder"
        / "scripts"
        / "scaffold_archive_index.py"
    )
    out_dir = tmp_path / "archive-index"

    result = subprocess.run(
        [sys.executable, str(script), str(out_dir)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (out_dir / "README.md").exists()
    assert (out_dir / "config" / "index-policy.yaml").exists()
    assert (out_dir / "sql" / "schema.sql").exists()
    assert (out_dir / "docs" / "promotion-rules.md").exists()
    assert (out_dir / "source" / "downloads").is_dir()
    assert (out_dir / "source" / "manifests").is_dir()
    assert (out_dir / "source" / "extracted").is_dir()
    assert (out_dir / "source" / "cache").is_dir()
    assert (out_dir / "artifacts" / "registry").is_dir()
    assert (out_dir / "artifacts" / "extracts").is_dir()
    assert (out_dir / "artifacts" / "derived").is_dir()
    assert (out_dir / "artifacts" / "state" / "source-freshness.json").exists()
    assert (out_dir / "scripts" / "archive_verifier.py").exists()
    assert (out_dir / "scripts" / "rebuild_index.py").exists()
    assert (out_dir / "scripts" / "check_index_consistency.py").exists()
    assert (out_dir / "scripts" / "refresh_latest_source.py").exists()
    assert (out_dir / "scripts" / "sync_source_registry.py").exists()
    assert (out_dir / "scripts" / "ingest_source_document.py").exists()
    assert (out_dir / "scripts" / "consult_archive.py").exists()
    assert (out_dir / "scripts" / "run_archive_check.py").exists()
    assert (out_dir / "scripts" / "run_archive_evals.py").exists()
    assert (out_dir / "scripts" / "scaffold_archive_evals.py").exists()
    assert (out_dir / "archive-evals" / "manifest.json").exists()
    assert (out_dir / "archive-evals" / "README.md").exists()
    readme = (out_dir / "README.md").read_text(encoding="utf-8")
    agents = (out_dir / "AGENTS.md").read_text(encoding="utf-8")
    assert "outside the Ledger repo" in readme
    assert "uv run python scripts/consult_archive.py" in readme
    assert "uv run ledger archive rebuild-source-indexes --root ." in readme
    assert "uv run python scripts/run_archive_evals.py run ." in readme
    assert "uv run ledger archive rebuild-source-indexes --root ." in agents

    local_consult = subprocess.run(
        [
            sys.executable,
            str(out_dir / "scripts" / "consult_archive.py"),
            "--archive-root",
            str(out_dir),
            "--question",
            "What does the archive know about VAT?",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert local_consult.returncode == 0, local_consult.stderr
    consult_payload = json.loads(local_consult.stdout)
    assert consult_payload["outcome"] == "expand"
    assert Path(consult_payload["audit_path"]).exists()

    local_eval = subprocess.run(
        [sys.executable, str(out_dir / "scripts" / "run_archive_evals.py"), "run", str(out_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert local_eval.returncode == 0, local_eval.stderr


def test_archive_index_skill_scaffold_preserves_existing_freshness_state(tmp_path: Path) -> None:
    script = (
        Path(__file__).resolve().parents[2]
        / "skills"
        / "archive-index-builder"
        / "scripts"
        / "scaffold_archive_index.py"
    )
    out_dir = tmp_path / "archive-index"

    result = subprocess.run(
        [sys.executable, str(script), str(out_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    freshness_path = out_dir / "artifacts" / "state" / "source-freshness.json"
    freshness_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "families": {
                    "debates": {
                        "last_sync_ok": True,
                        "newest_discovered_doc_id": "DAR-I-091",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(script), str(out_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(freshness_path.read_text(encoding="utf-8"))
    assert payload["families"]["debates"]["newest_discovered_doc_id"] == "DAR-I-091"
