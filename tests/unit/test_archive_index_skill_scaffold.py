from __future__ import annotations

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
    assert (out_dir / "artifacts" / "registry").is_dir()
    assert (out_dir / "artifacts" / "extracts").is_dir()
    assert (out_dir / "artifacts" / "derived").is_dir()
    assert (out_dir / "scripts" / "archive_verifier.py").exists()
    assert (out_dir / "scripts" / "rebuild_index.py").exists()
    assert (out_dir / "scripts" / "check_index_consistency.py").exists()
    assert (out_dir / "scripts" / "run_archive_check.py").exists()
