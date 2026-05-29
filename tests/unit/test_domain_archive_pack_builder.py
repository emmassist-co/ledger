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
        archive_root / "recipes" / "source-playbooks.yaml",
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
        archive_root / "domain" / "OPERATIONS.md",
        archive_root / "domain" / "ENRICHMENT_PROTOCOL.md",
        archive_root / "domain" / "coverage-ledger.yaml",
        archive_root / "domain" / "expansion-report-template.md",
        archive_root / "templates" / "domain-pack" / "claims.json",
        archive_root / "templates" / "domain-pack" / "answer.json",
        archive_root / "templates" / "domain-pack" / "decision.json",
        archive_root / "templates" / "domain-pack" / "expansion-plan.json",
        archive_root / "skills" / "portuguese-tax-archive-operator" / "SKILL.md",
        archive_root / "archive-evals" / "thresholds.json",
        archive_root / "domain-benchmarks" / "thresholds.json",
    ]
    for path in expected_files:
        assert path.exists(), path

    skill_text = (archive_root / "skills" / "portuguese-tax-archive-operator" / "SKILL.md").read_text()
    assert "recipes/source-families.yaml" in skill_text
    assert "recipes/source-playbooks.yaml" in skill_text
    assert "recipes/source-acquisition.yaml" in skill_text
    assert "recipes/extract-units.yaml" in skill_text
    assert "recipes/persistence-rules.yaml" in skill_text
    assert "recipes/fact-intake.yaml" in skill_text
    assert "recipes/answer-contract.yaml" in skill_text
    assert "recipes/support-hierarchy.yaml" in skill_text
    assert "recipes/confirmation-thresholds.yaml" in skill_text
    assert "domain/coverage-ledger.yaml" in skill_text
    assert "domain/OPERATIONS.md" in skill_text
    assert "domain/ENRICHMENT_PROTOCOL.md" in skill_text
    assert "templates/domain-pack/claims.json" in skill_text
    assert "templates/domain-pack/answer.json" in skill_text
    assert "templates/domain-pack/decision.json" in skill_text
    assert "templates/domain-pack/expansion-plan.json" in skill_text
    assert "check_coverage_state" in skill_text
    assert "auto_expand_when_below_target: true" in skill_text
    assert "uv run python scripts/run_archive_check.py" in skill_text
    assert "check_confirmation_boundary" in skill_text
    assert "allowed source families" in skill_text.lower()
    assert "bounded refinement pass" in skill_text
    assert "bounded failure" in skill_text.lower()

    protocol_text = (archive_root / "domain" / "ENRICHMENT_PROTOCOL.md").read_text()
    assert "## Step 1: Classify the question" in protocol_text
    assert "## Step 3: Decide fetch vs ask-user" in protocol_text
    assert "Run `check_coverage_state` when the question may sit on a partial topic or known support gap." in protocol_text
    assert "Record the decision with `templates/domain-pack/decision.json`." in protocol_text
    assert "Distinguish `provisional` from `at_target` answer quality before stopping." in protocol_text
    assert "Keep the first search pass inside the question shape's preferred source family" in protocol_text
    assert "Stop boundedly after the question shape's refinement budget" in protocol_text

    operations_text = (archive_root / "domain" / "OPERATIONS.md").read_text()
    assert "check_coverage_state --archive-root . --term" in operations_text
    assert "- Refresh required before answer: `true`." in operations_text
    assert "question shape's allowed source families" in operations_text

    acquisition = (archive_root / "recipes" / "source-acquisition.yaml").read_text()
    assert "question_shape_policies:" in acquisition
    assert "preferred_source_family: statutes" in acquisition
    assert "initial_query_budget: 3" in acquisition
    assert "allow_second_stage_refinement: true" in acquisition

    playbooks = (archive_root / "recipes" / "source-playbooks.yaml").read_text()
    assert "question_shape_search_guidance:" in playbooks
    assert "query_templates:" in playbooks

    coverage_ledger = (archive_root / "domain" / "coverage-ledger.yaml").read_text()
    assert "provisional_weak_slices:" in coverage_ledger
    assert "Use provisional_weak_slices for likely below-target support" in coverage_ledger
    assert "Suggested provisional_weak_slices entry keys:" in coverage_ledger
    assert "Move a provisional weak slice to support_gaps" in coverage_ledger
    assert "Suggested support_gaps entry keys:" in coverage_ledger

    scenario_payload = json.loads(
        (archive_root / "archive-evals" / "scenarios" / "boundary-missing-facts.json").read_text()
    )
    assert scenario_payload["case_metadata"]["tier"] == "golden"
    assert scenario_payload["case_metadata"]["critical_path"] is True
    assert scenario_payload["case_metadata"]["failure_class"] == "missing_facts"
    assert scenario_payload["answer_expectations"]["response_mode"] == "answer_with_missing_facts"
    assert scenario_payload["answer_expectations"]["expected_decision_action"] == "answer"
    assert scenario_payload["answer_expectations"]["minimum_quality_status"] == "provisional"
    assert scenario_payload["answer_expectations"]["required_answer_sections"] == [
        "rule_found",
        "missing_facts",
        "evidence_type",
        "verified_at",
    ]

    decision_template = json.loads(
        (archive_root / "templates" / "domain-pack" / "decision.json").read_text()
    )
    assert decision_template["quality_status"] == "below_target"
    assert decision_template["follow_up_action"] == "expand"

    answer_contract = (archive_root / "recipes" / "answer-contract.yaml").read_text()
    assert "auto_expand_when_below_target: true" in answer_contract
    assert "allow_non_expand_actions_when_below_target:" in answer_contract

    expansion_template = json.loads(
        (archive_root / "templates" / "domain-pack" / "expansion-plan.json").read_text()
    )
    assert expansion_template["question_shape"] == "rule_lookup"
    assert expansion_template["search_stage"] == "initial"
    assert expansion_template["query_terms"] == ["replace-with-query-1"]

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


def test_domain_pack_scaffold_rejects_incomplete_profile(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    archive_root = tmp_path / "broken-archive"

    scaffold_archive = root / "skills" / "archive-index-builder" / "scripts" / "scaffold_archive_index.py"
    scaffold_pack = root / "skills" / "domain-archive-pack-builder" / "scripts" / "scaffold_domain_pack.py"

    result = subprocess.run(
        [sys.executable, str(scaffold_archive), str(archive_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    profile_path = archive_root / "recipes" / "domain-profile.yaml"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(
        PROFILE_YAML.replace("    persistence_default: on_use\n", "", 1),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(scaffold_pack), str(archive_root), "--profile", str(profile_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert any("source_families[0] missing required keys: persistence_default" in failure for failure in payload["failures"])
