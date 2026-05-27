from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_domain_pack_benchmark_improves_domain_pack_compliance_without_hurting_archive_eval() -> None:
    root = Path(__file__).resolve().parents[2]
    script = root / "skills" / "domain-archive-pack-builder" / "scripts" / "benchmark_domain_pack.py"
    example = root / "examples" / "dr-cirs-reinvestment"

    result = subprocess.run(
        [sys.executable, str(script), str(example), "--trials", "2"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    assert payload["example"] == "dr-cirs-reinvestment"
    assert payload["trials"] == 2
    assert payload["with_domain_pack"]["domain_pack_pass_rate_mean"] > payload["baseline"]["domain_pack_pass_rate_mean"]
    assert payload["delta"]["domain_pack_pass_rate"] > 0
    assert payload["delta"]["archive_clean_pass_rate"] == 0.0
    assert payload["family_scores"]["fact_intake"]["delta"] > 0
    assert payload["family_scores"]["freshness"]["delta"] > 0
    assert payload["family_scores"]["exact_wording"]["delta"] > 0
    assert payload["family_scores"]["exceptions"]["delta"] > 0
    assert payload["family_scores"]["expansion"]["delta"] > 0
    assert payload["family_scores"]["answer_contract"]["delta"] > 0
    assert payload["family_scores"]["support_hierarchy"]["delta"] > 0
    assert payload["family_scores"]["confirmation_boundary"]["delta"] > 0
    assert payload["family_scores"]["scope_boundary"]["delta"] > 0
    assert payload["thresholds"]["checked"] is True
    assert payload["thresholds"]["ok"] is True
    assert payload["last_trial"]["packed_validate"]["ok"] is True
