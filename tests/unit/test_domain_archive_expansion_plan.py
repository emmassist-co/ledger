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
exception_classes:
  - timing
  - eligibility
answer_sections:
  - rule_found
  - missing_facts
  - evidence_type
  - verified_at
"""


def test_expansion_plan_validator_accepts_valid_plan_and_blocks_bad_exact_wording_materialization(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    archive_root = tmp_path / "tax-archive"

    scaffold_archive = root / "skills" / "archive-index-builder" / "scripts" / "scaffold_archive_index.py"
    scaffold_pack = root / "skills" / "domain-archive-pack-builder" / "scripts" / "scaffold_domain_pack.py"
    check_plan = root / "skills" / "domain-archive-pack-builder" / "scripts" / "check_expansion_plan.py"

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

    valid_plan = {
        "task_type": "rule_lookup",
        "question_shape": "rule_lookup",
        "source_family": "statutes",
        "source_url": "https://example.gov/statute/43",
        "unit_type": "article",
        "materialize_as": "extract",
        "persistence_action": "persist",
        "search_stage": "initial",
        "query_terms": ["codigo irs artigo 43"],
        "reason": "Need exact rule wording for article lookup",
        "exact_wording_claim": True,
    }
    valid_plan_path = archive_root / "valid-plan.json"
    valid_plan_path.write_text(json.dumps(valid_plan), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(check_plan), str(archive_root), "--plan-json", str(valid_plan_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["ok"] is True

    invalid_plan = {
        **valid_plan,
        "materialize_as": "derived_summary",
    }
    invalid_plan_path = archive_root / "invalid-plan.json"
    invalid_plan_path.write_text(json.dumps(invalid_plan), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(check_plan), str(archive_root), "--plan-json", str(invalid_plan_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert any(failure["field"] == "materialize_as" for failure in payload["failures"])


def test_expansion_plan_validator_blocks_over_budget_refinement(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    archive_root = tmp_path / "tax-archive"

    scaffold_archive = root / "skills" / "archive-index-builder" / "scripts" / "scaffold_archive_index.py"
    scaffold_pack = root / "skills" / "domain-archive-pack-builder" / "scripts" / "scaffold_domain_pack.py"
    check_plan = root / "skills" / "domain-archive-pack-builder" / "scripts" / "check_expansion_plan.py"

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

    invalid_plan = {
        "task_type": "rule_lookup",
        "question_shape": "rule_lookup",
        "source_family": "statutes",
        "source_url": "https://example.gov/statute/43",
        "unit_type": "article",
        "materialize_as": "extract",
        "persistence_action": "persist",
        "search_stage": "refinement",
        "query_terms": [
            "codigo irs artigo 43",
            "mais valias saldo excecao",
            "residentes apoio publico",
        ],
        "reason": "Need bounded refinement on the canonical source family",
        "exact_wording_claim": True,
    }
    invalid_plan_path = archive_root / "invalid-refinement-plan.json"
    invalid_plan_path.write_text(json.dumps(invalid_plan), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(check_plan), str(archive_root), "--plan-json", str(invalid_plan_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert any("refinement search exceeds budget" in failure["reason"] for failure in payload["failures"])
