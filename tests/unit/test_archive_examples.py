from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_example_archives_run_eval_successfully() -> None:
    root = Path(__file__).resolve().parents[2]
    script = root / "skills" / "archive-evals" / "scripts" / "run_archive_evals.py"

    for example_name in ("session-like", "legal-like"):
        archive_root = root / "examples" / example_name
        result = subprocess.run(
            [sys.executable, str(script), "run", str(archive_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

        report = json.loads((archive_root / "archive-evals" / "reports" / "latest.json").read_text())
        summary = report["summary"]
        assert summary["common_failure_modes"] == []
        assert summary["retrieval_metrics"]["scenario_count"] == 3
        assert summary["retrieval_metrics"]["overall"]["hit_at_k"] == 1.0
        assert summary["retrieval_metrics"]["overall"]["mrr_at_k"] == 1.0
