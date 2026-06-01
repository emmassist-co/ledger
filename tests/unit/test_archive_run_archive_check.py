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


def test_run_archive_check_support_hierarchy_infers_support_from_evidence_artifact(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    scaffold_archive = root / "skills" / "archive-index-builder" / "scripts" / "scaffold_archive_index.py"
    scaffold_pack = root / "skills" / "domain-archive-pack-builder" / "scripts" / "scaffold_domain_pack.py"
    archive_root = tmp_path / "archive-index"

    result = subprocess.run(
        [sys.executable, str(scaffold_archive), str(archive_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    profile = """schema_version: 1
domain_name: Test Legal Archive
domain_slug: test-legal-archive
domain_summary: Test pack.
risk_class: high
operating_mode: accuracy_first
volatility: annual
fact_sensitivity: helpful
exception_density: medium
exact_wording: critical
source_families:
  - name: statutes
    canonical_source_type: official
    retrieval_unit: article
    persistence_default: on_use
required_facts:
  - fact_id: time_period
    prompt: What period applies?
    required_for:
      - rule_lookup
exception_classes:
  - timing
answer_sections:
  - rule_found
  - evidence_type
  - verified_at
currentness:
  enabled: true
  current_question_shapes:
    - rule_lookup
  statuses:
    - current
    - stale
    - superseded
    - unproven
  proof_bundle_fields:
    - checked_at
    - canonical_source_url
"""
    profile_path = archive_root / "recipes" / "domain-profile.yaml"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(profile, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(scaffold_pack), str(archive_root), "--profile", str(profile_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    documents_path = archive_root / "index" / "documents.jsonl"
    documents_path.parent.mkdir(parents=True, exist_ok=True)
    documents_path.write_text(
        json.dumps(
                {
                    "artifact_id": "art-43",
                    "title": "Artigo 43",
                    "artifact_type": "extract",
                    "search_text": "resident taxpayers 50 amount article 43",
                }
            )
        + "\n",
        encoding="utf-8",
    )

    helper = archive_root / "scripts" / "run_archive_check.py"
    claims = {
        "claims": [
            {
                "claim_id": "c1",
                "decisive": True,
                "evidence_ids": ["art-43"],
            }
        ]
    }
    result = subprocess.run(
        [
            sys.executable,
            str(helper),
            "check_support_hierarchy",
            "--archive-root",
            str(archive_root),
            "--claims-payload",
            json.dumps(claims),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["check"] == "check_support_hierarchy"
    assert payload["ok"] is True
    assert payload["counts"]["claims_checked"] == 1


def test_run_archive_check_currentness_blocks_superseded_status(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    scaffold_archive = root / "skills" / "archive-index-builder" / "scripts" / "scaffold_archive_index.py"
    scaffold_pack = root / "skills" / "domain-archive-pack-builder" / "scripts" / "scaffold_domain_pack.py"
    archive_root = tmp_path / "archive-index"

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
        """schema_version: 1
domain_name: Test Legal Archive
domain_slug: test-legal-archive
domain_summary: Test pack.
risk_class: high
operating_mode: accuracy_first
volatility: annual
fact_sensitivity: helpful
exception_density: medium
exact_wording: critical
source_families:
  - name: statutes
    canonical_source_type: official
    retrieval_unit: article
    persistence_default: on_use
required_facts:
  - fact_id: time_period
    prompt: What period applies?
    required_for:
      - rule_lookup
exception_classes:
  - timing
answer_sections:
  - rule_found
  - evidence_type
  - verified_at
currentness:
  enabled: true
  current_question_shapes:
    - rule_lookup
  statuses:
    - current
    - stale
    - superseded
    - unproven
  proof_bundle_fields:
    - checked_at
    - canonical_source_url
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(scaffold_pack), str(archive_root), "--profile", str(profile_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    helper = archive_root / "scripts" / "run_archive_check.py"
    currentness = {
        "question_shape": "rule_lookup",
        "status": "superseded",
        "checked_at": "2026-06-01T00:00:00Z",
        "canonical_source_url": "https://example.com/dr/1",
        "reason": "A newer consolidated text exists.",
    }
    result = subprocess.run(
        [
            sys.executable,
            str(helper),
            "check_currentness",
            "--archive-root",
            str(archive_root),
            "--currentness-payload",
            json.dumps(currentness),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stderr
    payload = json.loads(result.stdout)
    assert payload["check"] == "check_currentness"
    assert payload["ok"] is False
    assert payload["status"] == "superseded"


def test_run_archive_check_does_not_delete_user_supplied_payload_file(tmp_path: Path) -> None:
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

    payload_path = archive_root / "claims.json"
    payload_path.write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "claim_id": "c1",
                        "exact_wording": True,
                        "support_kind": "derived_summary",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    helper = archive_root / "scripts" / "run_archive_check.py"
    result = subprocess.run(
        [
            sys.executable,
            str(helper),
            "check_exact_wording",
            "--archive-root",
            str(archive_root),
            "--claims-json",
            str(payload_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert payload_path.exists()


def test_run_archive_check_claim_support_requires_indexed_evidence_ids(tmp_path: Path) -> None:
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

    documents_path = archive_root / "index" / "documents.jsonl"
    documents_path.parent.mkdir(parents=True, exist_ok=True)
    documents_path.write_text(
        json.dumps(
            {
                "artifact_id": "art-43",
                "title": "Artigo 43",
                "artifact_type": "extract",
                "search_text": "resident taxpayers 50 amount article 43",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    helper = archive_root / "scripts" / "run_archive_check.py"
    claims = {
        "claims": [
            {
                "claim_id": "c1",
                "evidence_ids": ["missing-artifact-id"],
            }
        ]
    }
    result = subprocess.run(
        [
            sys.executable,
            str(helper),
            "check_claim_support",
            "--archive-root",
            str(archive_root),
            "--claims-payload",
            json.dumps(claims),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stderr
    payload = json.loads(result.stdout)
    assert payload["check"] == "check_claim_support"
    assert payload["ok"] is False
    assert payload["failures"][0]["reason"] == "evidence_ids not present in archive index"


def test_run_archive_check_coverage_matches_natural_language_query_tokens(tmp_path: Path) -> None:
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

    documents_path = archive_root / "index" / "documents.jsonl"
    documents_path.parent.mkdir(parents=True, exist_ok=True)
    documents_path.write_text(
        json.dumps(
            {
                "artifact_id": "note-cirs-hpp-reinvestment",
                "title": "HPP reinvestment note",
                "artifact_type": "consolidation_note",
                "search_text": "sale proceeds repayment loan reinvestment own permanent home",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    helper = archive_root / "scripts" / "run_archive_check.py"
    result = subprocess.run(
        [
            sys.executable,
            str(helper),
            "check_coverage",
            "--archive-root",
            str(archive_root),
            "--term",
            "gross sale price net realization amount",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["check"] == "check_coverage"
    assert payload["ok"] is True
    assert payload["counts"]["candidates"] >= 1


def test_run_archive_check_coverage_state_flags_known_support_gap(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    scaffold_archive = root / "skills" / "archive-index-builder" / "scripts" / "scaffold_archive_index.py"
    scaffold_pack = root / "skills" / "domain-archive-pack-builder" / "scripts" / "scaffold_domain_pack.py"
    archive_root = tmp_path / "archive-index"

    result = subprocess.run(
        [sys.executable, str(scaffold_archive), str(archive_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    profile = """schema_version: 1
domain_name: Test Legal Archive
domain_slug: test-legal-archive
domain_summary: Test pack.
risk_class: high
operating_mode: accuracy_first
volatility: annual
fact_sensitivity: helpful
exception_density: medium
exact_wording: critical
source_families:
  - name: statutes
    canonical_source_type: official
    retrieval_unit: article
    persistence_default: on_use
required_facts:
  - fact_id: time_period
    prompt: What period applies?
    required_for:
      - rule_lookup
exception_classes:
  - timing
answer_sections:
  - rule_found
  - evidence_type
  - verified_at
"""
    profile_path = archive_root / "recipes" / "domain-profile.yaml"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(profile, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(scaffold_pack), str(archive_root), "--profile", str(profile_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    coverage_path = archive_root / "domain" / "coverage-ledger.yaml"
    coverage_path.write_text(
        """schema_version: 1
domain_slug: test-legal-archive
coverage_status: seeded
topics: []
provisional_weak_slices: []
partial_topics: []
stale_topics: []
support_gaps:
  - topic: cirs_article_43_resident_gains
    labels:
      - article 43
      - resident gains 50 percent
    task_types:
      - rule_lookup
    required_support: extract
    current_support: article_block
    quality_status: below_target
    follow_up_action: expand
    source_family: statutes
    artifact_ids:
      - art-cirs-43
notes:
  - Update this ledger as the archive grows.
  - Use provisional_weak_slices for likely below-target support that has not been fully confirmed yet.
  - Use support_gaps when the archive can answer provisionally but should still be enriched to reach target quality.
  - Move a provisional weak slice to support_gaps when the weakness is confirmed, clear it when stronger local support proves the suspicion unnecessary, and mark it superseded when a newer slice replaces the old concern.
  - Suggested provisional_weak_slices entry keys: topic, labels, task_types, suspected_support_gap, current_support, reason, source_family, artifact_ids, notes.
""",
        encoding="utf-8",
    )

    helper = archive_root / "scripts" / "run_archive_check.py"
    result = subprocess.run(
        [
            sys.executable,
            str(helper),
            "check_coverage_state",
            "--archive-root",
            str(archive_root),
            "--term",
            "resident gains article 43",
            "--task-type",
            "rule_lookup",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stderr
    payload = json.loads(result.stdout)
    assert payload["check"] == "check_coverage_state"
    assert payload["ok"] is False
    assert payload["status"] == "known_below_target"
    assert payload["suggested_action"] == "expand"
    assert payload["counts"]["matched_provisional_weak_slices"] == 0
    assert payload["counts"]["matched_support_gaps"] == 1


def test_run_archive_check_coverage_state_flags_provisional_weak_slice(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    scaffold_archive = root / "skills" / "archive-index-builder" / "scripts" / "scaffold_archive_index.py"
    scaffold_pack = root / "skills" / "domain-archive-pack-builder" / "scripts" / "scaffold_domain_pack.py"
    archive_root = tmp_path / "archive-index"

    result = subprocess.run(
        [sys.executable, str(scaffold_archive), str(archive_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    profile = """schema_version: 1
domain_name: Test Legal Archive
domain_slug: test-legal-archive
domain_summary: Test pack.
risk_class: high
operating_mode: accuracy_first
volatility: annual
fact_sensitivity: helpful
exception_density: medium
exact_wording: critical
source_families:
  - name: statutes
    canonical_source_type: official
    retrieval_unit: article
    persistence_default: on_use
required_facts:
  - fact_id: time_period
    prompt: What period applies?
    required_for:
      - rule_lookup
exception_classes:
  - timing
answer_sections:
  - rule_found
  - evidence_type
  - verified_at
"""
    profile_path = archive_root / "recipes" / "domain-profile.yaml"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(profile, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(scaffold_pack), str(archive_root), "--profile", str(profile_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    coverage_path = archive_root / "domain" / "coverage-ledger.yaml"
    coverage_path.write_text(
        """schema_version: 1
domain_slug: test-legal-archive
coverage_status: seeded
topics: []
provisional_weak_slices:
  - topic: cirs_article_43_resident_gains
    labels:
      - article 43
      - resident gains 50 percent
    task_types:
      - rule_lookup
    suspected_support_gap: missing exception handling
    current_support: article_block
    reason: local article support may omit the decisive exception
    source_family: statutes
    artifact_ids:
      - art-cirs-43
partial_topics: []
stale_topics: []
support_gaps: []
notes:
  - Update this ledger as the archive grows.
  - Use provisional_weak_slices for likely below-target support that has not been fully confirmed yet.
  - Use partial_topics and stale_topics to avoid overclaiming coverage.
  - Use support_gaps when the archive can answer provisionally but should still be enriched to reach target quality.
  - Move a provisional weak slice to support_gaps when the weakness is confirmed, clear it when stronger local support proves the suspicion unnecessary, and mark it superseded when a newer slice replaces the old concern.
  - Suggested provisional_weak_slices entry keys: topic, labels, task_types, suspected_support_gap, current_support, reason, source_family, artifact_ids, notes.
  - Suggested support_gaps entry keys: topic, labels, task_types, required_support, current_support, quality_status, follow_up_action, source_family, artifact_ids, notes.
""",
        encoding="utf-8",
    )

    helper = archive_root / "scripts" / "run_archive_check.py"
    result = subprocess.run(
        [
            sys.executable,
            str(helper),
            "check_coverage_state",
            "--archive-root",
            str(archive_root),
            "--term",
            "resident gains article 43",
            "--task-type",
            "rule_lookup",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stderr
    payload = json.loads(result.stdout)
    assert payload["check"] == "check_coverage_state"
    assert payload["ok"] is False
    assert payload["status"] == "likely_below_target"
    assert payload["suggested_action"] == "expand"
    assert payload["counts"]["matched_provisional_weak_slices"] == 1
    assert payload["counts"]["matched_support_gaps"] == 0


def test_run_archive_check_auto_expand_decision_blocks_direct_answer_on_known_gap(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    scaffold_archive = root / "skills" / "archive-index-builder" / "scripts" / "scaffold_archive_index.py"
    scaffold_pack = root / "skills" / "domain-archive-pack-builder" / "scripts" / "scaffold_domain_pack.py"
    archive_root = tmp_path / "archive-index"

    result = subprocess.run(
        [sys.executable, str(scaffold_archive), str(archive_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    profile = """schema_version: 1
domain_name: Test Legal Archive
domain_slug: test-legal-archive
domain_summary: Test pack.
risk_class: high
operating_mode: accuracy_first
volatility: annual
fact_sensitivity: helpful
exception_density: medium
exact_wording: critical
source_families:
  - name: statutes
    canonical_source_type: official
    retrieval_unit: article
    persistence_default: on_use
required_facts:
  - fact_id: time_period
    prompt: What period applies?
    required_for:
      - rule_lookup
exception_classes:
  - timing
answer_sections:
  - rule_found
  - evidence_type
  - verified_at
"""
    profile_path = archive_root / "recipes" / "domain-profile.yaml"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(profile, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(scaffold_pack), str(archive_root), "--profile", str(profile_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    coverage_path = archive_root / "domain" / "coverage-ledger.yaml"
    coverage_path.write_text(
        """schema_version: 1
domain_slug: test-legal-archive
coverage_status: seeded
topics: []
provisional_weak_slices: []
partial_topics: []
stale_topics: []
support_gaps:
  - topic: cirs_article_43_resident_gains
    labels:
      - article 43
    task_types:
      - rule_lookup
    required_support: extract
    current_support: article_block
    quality_status: below_target
    follow_up_action: expand
    source_family: statutes
    artifact_ids:
      - art-cirs-43
notes:
  - Update this ledger as the archive grows.
  - Use provisional_weak_slices for likely below-target support that has not been fully confirmed yet.
  - Use support_gaps when the archive can answer provisionally but should still be enriched to reach target quality.
  - Move a provisional weak slice to support_gaps when the weakness is confirmed, clear it when stronger local support proves the suspicion unnecessary, and mark it superseded when a newer slice replaces the old concern.
  - Suggested provisional_weak_slices entry keys: topic, labels, task_types, suspected_support_gap, current_support, reason, source_family, artifact_ids, notes.
""",
        encoding="utf-8",
    )

    helper = archive_root / "scripts" / "run_archive_check.py"
    decision = {
        "action": "answer",
        "reason": "found a local article block",
        "source_type": "official",
        "scope_status": "in_bounds",
        "artifact_kind": "reusable",
        "quality_status": "below_target",
        "follow_up_action": "expand",
    }
    result = subprocess.run(
        [
            sys.executable,
            str(helper),
            "check_auto_expand_decision",
            "--archive-root",
            str(archive_root),
            "--term",
            "article 43",
            "--task-type",
            "rule_lookup",
            "--decision-payload",
            json.dumps(decision),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stderr
    payload = json.loads(result.stdout)
    assert payload["check"] == "check_auto_expand_decision"
    assert payload["ok"] is False
    assert payload["counts"]["matched_provisional_weak_slices"] == 0
    assert payload["failures"][0]["actual_action"] == "answer"


def test_run_archive_check_decision_record_accepts_ask_user_without_artifact_kind(tmp_path: Path) -> None:
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
    decision = {
        "action": "ask_user",
        "reason": "missing user facts for case application",
        "source_type": "official",
        "scope_status": "insufficient_input",
    }
    result = subprocess.run(
        [
            sys.executable,
            str(helper),
            "check_decision_record",
            "--archive-root",
            str(archive_root),
            "--decision-payload",
            json.dumps(decision),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["check"] == "check_decision_record"
    assert payload["ok"] is True


def test_run_archive_check_registers_provisional_weak_slice_from_expand_decision(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    scaffold_archive = root / "skills" / "archive-index-builder" / "scripts" / "scaffold_archive_index.py"
    scaffold_pack = root / "skills" / "domain-archive-pack-builder" / "scripts" / "scaffold_domain_pack.py"
    archive_root = tmp_path / "archive-index"

    result = subprocess.run(
        [sys.executable, str(scaffold_archive), str(archive_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    profile = """schema_version: 1
domain_name: Test Legal Archive
domain_slug: test-legal-archive
domain_summary: Test pack.
risk_class: high
operating_mode: accuracy_first
volatility: annual
fact_sensitivity: helpful
exception_density: medium
exact_wording: critical
source_families:
  - name: statutes
    canonical_source_type: official
    retrieval_unit: article
    persistence_default: on_use
required_facts:
  - fact_id: time_period
    prompt: What period applies?
    required_for:
      - rule_lookup
exception_classes:
  - timing
answer_sections:
  - rule_found
  - evidence_type
  - verified_at
"""
    profile_path = archive_root / "recipes" / "domain-profile.yaml"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(profile, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(scaffold_pack), str(archive_root), "--profile", str(profile_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    documents_path = archive_root / "index" / "documents.jsonl"
    documents_path.parent.mkdir(parents=True, exist_ok=True)
    documents_path.write_text(
        json.dumps(
            {
                "artifact_id": "note-hpp",
                "title": "HPP note",
                "artifact_type": "consolidation_note",
                "search_text": "reinvestimento hpp excecoes casos limite",
            }
        )
        + "\n"
        + json.dumps(
            {
                "artifact_id": "ext-art10",
                "title": "Artigo 10 extract",
                "artifact_type": "extract",
                "search_text": "reinvestimento hpp artigo 10",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    helper = archive_root / "scripts" / "run_archive_check.py"
    decision = {
        "action": "expand",
        "reason": "Current local support covers the core rule but not the exception-heavy edge cases.",
        "source_type": "official",
        "scope_status": "in_bounds",
        "artifact_kind": "reusable",
        "quality_status": "provisional",
        "source_family": "statutes",
        "current_support": "consolidation_note",
        "suspected_support_gap": "edge_case_vertical",
        "artifact_ids": ["note-hpp", "ext-art10"],
        "match_terms": ["reinvestimento hpp excecoes", "casos limite reinvestimento hpp"],
    }
    result = subprocess.run(
        [
            sys.executable,
            str(helper),
            "register_provisional_weak_slice",
            "--archive-root",
            str(archive_root),
            "--term",
            "reinvestimento HPP exceções",
            "--task-type",
            "rule_lookup",
            "--decision-payload",
            json.dumps(decision),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["check"] == "register_provisional_weak_slice"
    assert payload["status"] == "created"

    coverage = (archive_root / "domain" / "coverage-ledger.yaml").read_text(encoding="utf-8")
    assert "provisional_weak_slices:" in coverage
    assert "reinvestimento HPP exce" in coverage
    assert "edge_case_vertical" in coverage


def test_run_archive_check_confirms_provisional_weak_slice_into_support_gap(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    scaffold_archive = root / "skills" / "archive-index-builder" / "scripts" / "scaffold_archive_index.py"
    scaffold_pack = root / "skills" / "domain-archive-pack-builder" / "scripts" / "scaffold_domain_pack.py"
    archive_root = tmp_path / "archive-index"

    result = subprocess.run(
        [sys.executable, str(scaffold_archive), str(archive_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    profile = """schema_version: 1
domain_name: Test Legal Archive
domain_slug: test-legal-archive
domain_summary: Test pack.
risk_class: high
operating_mode: accuracy_first
volatility: annual
fact_sensitivity: helpful
exception_density: medium
exact_wording: critical
source_families:
  - name: statutes
    canonical_source_type: official
    retrieval_unit: article
    persistence_default: on_use
required_facts:
  - fact_id: time_period
    prompt: What period applies?
    required_for:
      - rule_lookup
exception_classes:
  - timing
answer_sections:
  - rule_found
  - evidence_type
  - verified_at
"""
    profile_path = archive_root / "recipes" / "domain-profile.yaml"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(profile, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(scaffold_pack), str(archive_root), "--profile", str(profile_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    coverage_path = archive_root / "domain" / "coverage-ledger.yaml"
    coverage_path.write_text(
        """schema_version: 1
domain_slug: test-legal-archive
coverage_status: seeded
topics: []
provisional_weak_slices:
  - topic: hpp_edge_cases
    labels:
      - reinvestimento hpp excecoes
    task_types:
      - rule_lookup
    suspected_support_gap: edge_case_vertical
    current_support: consolidation_note
    reason: Core rule exists but edge cases remain thin.
    source_family: statutes
    artifact_ids:
      - note-hpp
    notes:
      - Registered automatically from expand decision.
partial_topics: []
stale_topics: []
support_gaps: []
notes:
  - Update this ledger as the archive grows.
  - Use provisional_weak_slices for likely below-target support that has not been fully confirmed yet.
  - Use support_gaps when the archive can answer provisionally but should still be enriched to reach target quality.
  - Move a provisional weak slice to support_gaps when the weakness is confirmed, clear it when stronger local support proves the suspicion unnecessary, and mark it superseded when a newer slice replaces the old concern.
  - Suggested provisional_weak_slices entry keys: topic, labels, task_types, suspected_support_gap, current_support, reason, source_family, artifact_ids, notes.
""",
        encoding="utf-8",
    )

    helper = archive_root / "scripts" / "run_archive_check.py"
    result = subprocess.run(
        [
            sys.executable,
            str(helper),
            "resolve_provisional_weak_slice",
            "--archive-root",
            str(archive_root),
            "--term",
            "reinvestimento hpp excecoes",
            "--task-type",
            "rule_lookup",
            "--resolution",
            "confirmed",
            "--resolution-payload",
            json.dumps({"note": "Confirmed after repeated exception-heavy misses."}),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["check"] == "resolve_provisional_weak_slice"
    assert payload["status"] == "confirmed"

    coverage = (archive_root / "domain" / "coverage-ledger.yaml").read_text(encoding="utf-8")
    assert "provisional_weak_slices: []" in coverage
    assert "support_gaps:" in coverage
    assert "required_support: extract" in coverage
    assert "Confirmed provisional weak slice" in coverage


def test_run_archive_check_blocks_over_budget_expansion_plan(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    scaffold_archive = root / "skills" / "archive-index-builder" / "scripts" / "scaffold_archive_index.py"
    scaffold_pack = root / "skills" / "domain-archive-pack-builder" / "scripts" / "scaffold_domain_pack.py"
    archive_root = tmp_path / "archive-index"

    result = subprocess.run(
        [sys.executable, str(scaffold_archive), str(archive_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    profile = """schema_version: 1
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
    profile_path = archive_root / "recipes" / "domain-profile.yaml"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(profile, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(scaffold_pack), str(archive_root), "--profile", str(profile_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    helper = archive_root / "scripts" / "run_archive_check.py"
    plan = {
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

    result = subprocess.run(
        [
            sys.executable,
            str(helper),
            "check_expansion_plan",
            "--archive-root",
            str(archive_root),
            "--plan-payload",
            json.dumps(plan),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert any("refinement search exceeds budget" in failure["reason"] for failure in payload["failures"])
