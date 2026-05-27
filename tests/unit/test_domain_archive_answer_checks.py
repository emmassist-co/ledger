from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROFILE_YAML = """schema_version: 1
domain_name: Portuguese Tax Archive
domain_slug: portuguese-tax-archive
domain_summary: Archive-first operating pack for Portuguese personal-tax rule lookup and scoped case application.
risk_class: high
operating_mode: accuracy_first
volatility: annual
fact_sensitivity: required
exception_density: high
exact_wording: critical
source_families:
  - name: statutes
    canonical_source_type: official
    retrieval_unit: article
    persistence_default: on_use
required_facts:
  - fact_id: residency
    prompt: Is the taxpayer resident in Portugal for the relevant tax year?
    required_for:
      - case_application
  - fact_id: tax_year
    prompt: What tax year or effective period does the question depend on?
    required_for:
      - case_application
exception_classes:
  - timing
  - eligibility
answer_sections:
  - rule_found
  - missing_facts
  - evidence_type
  - verified_at
"""


def test_support_hierarchy_and_confirmation_boundary_block_overclaiming(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    archive_root = tmp_path / "tax-archive"

    scaffold_archive = root / "skills" / "archive-index-builder" / "scripts" / "scaffold_archive_index.py"
    scaffold_pack = root / "skills" / "domain-archive-pack-builder" / "scripts" / "scaffold_domain_pack.py"
    check_support = root / "skills" / "domain-archive-pack-builder" / "scripts" / "check_support_hierarchy.py"
    check_confirmation = root / "skills" / "domain-archive-pack-builder" / "scripts" / "check_confirmation_boundary.py"

    result = subprocess.run(
        [sys.executable, str(scaffold_archive), str(archive_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    profile_path = archive_root / "recipes" / "domain-profile.yaml"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(PROFILE_YAML, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(scaffold_pack), str(archive_root), "--profile", str(profile_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    bad_claims = {
        "claims": [
            {
                "claim_id": "c1",
                "decisive": True,
                "support_type": "derived_summary",
            }
        ]
    }
    bad_claims_path = archive_root / "bad-claims.json"
    bad_claims_path.write_text(json.dumps(bad_claims), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(check_support), str(archive_root), "--claims-json", str(bad_claims_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout)["ok"] is False

    bad_answer = {
        "conclusion_level": "confirmed_from_provided_facts",
        "blocking_facts_confirmed": ["residency"],
        "blocking_facts_missing": ["tax_year"],
        "phrasing": "She is confirmed eligible.",
    }
    bad_answer_path = archive_root / "bad-answer.json"
    bad_answer_path.write_text(json.dumps(bad_answer), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(check_confirmation), str(archive_root), "--answer-json", str(bad_answer_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert any(failure["field"] == "conclusion_level" for failure in payload["failures"])
