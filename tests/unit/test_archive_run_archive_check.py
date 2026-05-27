from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_run_archive_check_accepts_inline_claims_payload_for_exact_wording(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    scaffold_archive = root / "skills" / "archive-index-builder" / "scripts" / "scaffold_archive_index.py"
    archive_root = tmp_path / "archive-index"

    result = subprocess.run(
        [sys.executable, str(scaffold_archive), str(archive_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    helper = archive_root / "scripts" / "run_archive_check.py"
    claims = {
        "claims": [
            {
                "claim_id": "c1",
                "exact_wording": True,
                "support_kind": "derived_summary",
            }
        ]
    }
    result = subprocess.run(
        [
            sys.executable,
            str(helper),
            "check_exact_wording",
            "--archive-root",
            str(archive_root),
            "--claims-payload",
            json.dumps(claims),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["check"] == "check_exact_wording"
    assert payload["ok"] is False
    assert payload["failures"][0]["reason"] == "exact wording requires raw_source or extract support"
