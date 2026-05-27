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
  - name: official_faqs
    canonical_source_type: official
    retrieval_unit: faq_entry
    persistence_default: on_use
required_facts:
  - fact_id: residency
    prompt: Is the taxpayer resident in Portugal for the relevant tax year?
    required_for:
      - case_application
  - fact_id: tax_year
    prompt: What tax year or effective period does the question depend on?
    required_for:
      - rule_lookup
      - case_application
exception_classes:
  - timing
  - eligibility
  - anti_abuse
answer_sections:
  - rule_found
  - missing_facts
  - evidence_type
  - verified_at
"""


def test_domain_pack_scaffold_and_validate(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    archive_root = tmp_path / "tax-archive"

    scaffold_archive = root / "skills" / "archive-index-builder" / "scripts" / "scaffold_archive_index.py"
    scaffold_pack = root / "skills" / "domain-archive-pack-builder" / "scripts" / "scaffold_domain_pack.py"
    validate_pack = root / "skills" / "domain-archive-pack-builder" / "scripts" / "validate_domain_pack.py"

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

    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["domain_slug"] == "portuguese-tax-archive"
    assert payload["generated"]["scenario_count"] >= 3

    expected_files = [
        archive_root / "recipes" / "source-families.yaml",
        archive_root / "recipes" / "source-acquisition.yaml",
        archive_root / "recipes" / "extract-units.yaml",
        archive_root / "recipes" / "persistence-rules.yaml",
        archive_root / "recipes" / "fact-intake.yaml",
        archive_root / "recipes" / "freshness-rules.yaml",
        archive_root / "recipes" / "exception-patterns.yaml",
        archive_root / "recipes" / "answer-contract.yaml",
        archive_root / "recipes" / "support-hierarchy.yaml",
        archive_root / "recipes" / "confirmation-thresholds.yaml",
        archive_root / "domain" / "DOMAIN.md",
        archive_root / "domain" / "coverage-ledger.yaml",
        archive_root / "domain" / "expansion-report-template.md",
        archive_root / "skills" / "portuguese-tax-archive-operator" / "SKILL.md",
        archive_root / "archive-evals" / "thresholds.json",
        archive_root / "domain-benchmarks" / "thresholds.json",
    ]
    for path in expected_files:
        assert path.exists(), path

    skill_text = (archive_root / "skills" / "portuguese-tax-archive-operator" / "SKILL.md").read_text()
    assert "recipes/source-families.yaml" in skill_text
    assert "recipes/source-acquisition.yaml" in skill_text
    assert "recipes/extract-units.yaml" in skill_text
    assert "recipes/persistence-rules.yaml" in skill_text
    assert "recipes/fact-intake.yaml" in skill_text
    assert "recipes/answer-contract.yaml" in skill_text
    assert "recipes/support-hierarchy.yaml" in skill_text
    assert "recipes/confirmation-thresholds.yaml" in skill_text
    assert "domain/coverage-ledger.yaml" in skill_text
    assert "uv run python scripts/run_archive_check.py" in skill_text
    assert "check_confirmation_boundary" in skill_text

    result = subprocess.run(
        [sys.executable, str(validate_pack), str(archive_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    validation = json.loads(result.stdout)
    assert validation["ok"] is True
    assert validation["domain_slug"] == "portuguese-tax-archive"
