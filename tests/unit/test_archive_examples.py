from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_example_archives_run_eval_successfully() -> None:
    root = Path(__file__).resolve().parents[2]
    script = root / "skills" / "archive-evals" / "scripts" / "run_archive_evals.py"
    expected = {
        "session-like": {"scenario_count": 3, "completion_pass_rate": 1.0, "clean_pass_rate": 1.0, "drift_rate": 0.0},
        "legal-like": {"scenario_count": 3, "completion_pass_rate": 1.0, "clean_pass_rate": 1.0, "drift_rate": 0.0},
        "dr-agenda-trabalho-digno": {"scenario_count": 4, "completion_pass_rate": 1.0, "clean_pass_rate": 1.0, "drift_rate": 0.0},
        "dr-cirs-reinvestment": {"scenario_count": 4, "completion_pass_rate": 1.0, "clean_pass_rate": 0.75, "drift_rate": 0.25},
    }

    for example_name, metrics in expected.items():
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
        assert summary["retrieval_metrics"]["scenario_count"] == metrics["scenario_count"]
        assert summary["retrieval_metrics"]["overall"]["hit_at_k"] == 1.0
        assert summary["retrieval_metrics"]["overall"]["mrr_at_k"] == 1.0
        assert summary["trajectory_metrics"]["scenario_count"] == metrics["scenario_count"]
        assert summary["trajectory_metrics"]["completion_pass_rate"] == metrics["completion_pass_rate"]
        assert summary["trajectory_metrics"]["clean_pass_rate"] == metrics["clean_pass_rate"]
        assert summary["trajectory_metrics"]["drift_rate"] == metrics["drift_rate"]
        assert "answer_quality_metrics" in summary
        assert summary["answer_quality_metrics"]["scenario_count"] == 0
        assert summary["thresholds"]["checked"] is True
        assert summary["thresholds"]["ok"] is True

        if example_name == "dr-cirs-reinvestment":
            assert any(result["status"] == "pass_with_drift" for result in report["results"])


def test_example_benchmark_summary_generates_successfully() -> None:
    root = Path(__file__).resolve().parents[2]
    script = root / "skills" / "archive-evals" / "scripts" / "run_archive_evals.py"

    result = subprocess.run(
        [sys.executable, str(script), "summarize-examples", str(root / "examples")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    summary_json = json.loads((root / "examples" / "benchmark-summary.json").read_text())
    summary_md = (root / "examples" / "benchmark-summary.md").read_text()
    assert summary_json["overall_ok"] is True
    assert len(summary_json["examples"]) >= 4
    assert "| Example | Scenarios |" in summary_md
