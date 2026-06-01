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


def test_run_archive_check_builds_and_validates_currentness_bundle(tmp_path: Path) -> None:
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
  - name: consolidated_legal_views
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

    artifact_path = archive_root / "artifacts" / "extracts" / "ext-test-currentness.md"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        """---
artifact_type: extract
artifact_id: ext-test-currentness
source_system: diariodarepublica.pt
source_url: https://diariodarepublica.pt/dr/legislacao-consolidada/decreto-lei/1966-34509075-122540650
source_document_id: '34509075'
title: Test currentness extract
verified_at: 2026-06-01
confidence: high
---
# Test currentness extract
""",
        encoding="utf-8",
    )

    freshness_path = archive_root / "artifacts" / "state" / "source-freshness.json"
    freshness_path.parent.mkdir(parents=True, exist_ok=True)
    freshness_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "families": {
                    "consolidated_legal_views": {
                        "last_listing_sync_at": "2026-06-01T16:09:00Z",
                        "last_sync_ok": True,
                        "newest_discovered_doc_id": "34509075",
                        "newest_temporary_doc_id": "34509075",
                        "newest_durable_doc_id": "34509075",
                    }
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rebuild = archive_root / "scripts" / "rebuild_index.py"
    result = subprocess.run(
        [sys.executable, str(rebuild)],
        capture_output=True,
        text=True,
        check=False,
        cwd=archive_root,
    )
    assert result.returncode == 0, result.stderr

    helper = archive_root / "scripts" / "run_archive_check.py"
    result = subprocess.run(
        [
            sys.executable,
            str(helper),
            "build_currentness_bundle",
            "--archive-root",
            str(archive_root),
            "--artifact-id",
            "ext-test-currentness",
            "--question-shape",
            "rule_lookup",
            "--source-family",
            "consolidated_legal_views",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    built = json.loads(result.stdout)
    bundle = built["currentness"]
    assert bundle["status"] == "current"
    assert bundle["checked_at"] == "2026-06-01T16:09:00Z"
    assert bundle["canonical_source_url"] == "https://diariodarepublica.pt/dr/legislacao-consolidada/decreto-lei/1966-34509075-122540650"
    assert bundle["relied_artifact_ids"] == ["ext-test-currentness"]

    result = subprocess.run(
        [
            sys.executable,
            str(helper),
            "check_currentness",
            "--archive-root",
            str(archive_root),
            "--currentness-payload",
            json.dumps(bundle),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["check"] == "check_currentness"
    assert payload["ok"] is True


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


def test_run_archive_check_source_freshness_validates_family_state(tmp_path: Path) -> None:
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

    (archive_root / "artifacts" / "state").mkdir(parents=True, exist_ok=True)
    (archive_root / "artifacts" / "state" / "source-freshness.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "families": {
                    "parliamentary_debates": {
                        "last_listing_sync_at": "2026-06-01T14:25:22Z",
                        "last_sync_ok": True,
                        "newest_discovered_doc_id": "DAR-I-091",
                        "newest_temporary_doc_id": "DAR-I-091",
                        "newest_durable_doc_id": "DAR-I-087",
                        "temporary_target_count": 1,
                        "last_transport": "curl",
                        "last_error": "",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    helper = archive_root / "scripts" / "run_archive_check.py"
    result = subprocess.run(
        [
            sys.executable,
            str(helper),
            "check_source_freshness",
            "--archive-root",
            str(archive_root),
            "--source-family",
            "parliamentary_debates",
            "--require-sync-ok",
            "--required-doc-role",
            "newest_discovered",
            "--required-doc-role",
            "newest_temporary",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["check"] == "check_source_freshness"
    assert payload["ok"] is True
    assert payload["resolved_roles"]["newest_discovered"] == "DAR-I-091"
    assert payload["resolved_roles"]["newest_temporary"] == "DAR-I-091"


def test_run_archive_check_source_registry_state_validates_temporary_navigation_assets(tmp_path: Path) -> None:
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

    cache_file = archive_root / "source" / "cache" / "DAR-I-091.pdf"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("pdf-bytes-placeholder", encoding="utf-8")
    page_index = archive_root / "source" / "index" / "pdf-pages" / "DAR-I-091.jsonl"
    page_index.parent.mkdir(parents=True, exist_ok=True)
    page_index.write_text('{"page": 1, "text": "example"}\n', encoding="utf-8")
    extracted_md = archive_root / "source" / "extracted" / "DAR-I-091.extracted.md"
    extracted_md.parent.mkdir(parents=True, exist_ok=True)
    extracted_md.write_text("# Extracted\n", encoding="utf-8")

    (archive_root / "artifacts" / "state").mkdir(parents=True, exist_ok=True)
    (archive_root / "artifacts" / "state" / "source-freshness.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "families": {
                    "parliamentary_debates": {
                        "last_listing_sync_at": "2026-06-01T14:25:22Z",
                        "last_sync_ok": True,
                        "newest_discovered_doc_id": "DAR-I-091",
                        "newest_temporary_doc_id": "DAR-I-091",
                        "newest_durable_doc_id": "DAR-I-087",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (archive_root / "artifacts" / "registry").mkdir(parents=True, exist_ok=True)
    (archive_root / "artifacts" / "registry" / "reg-dar-i-091.md").write_text(
        f"""---
artifact_type: registry
artifact_id: reg-dar-i-091
source_family: parliamentary_debates
source_document_id: DAR-I-091
discovery_state: temporary_indexed
temporary_local_file: {cache_file}
---
""",
        encoding="utf-8",
    )

    helper = archive_root / "scripts" / "run_archive_check.py"
    result = subprocess.run(
        [
            sys.executable,
            str(helper),
            "check_source_registry_state",
            "--archive-root",
            str(archive_root),
            "--source-family",
            "parliamentary_debates",
            "--doc-role",
            "newest_temporary",
            "--expected-state",
            "temporary_indexed",
            "--require-local-file",
            "--require-page-index",
            "--require-extracted-markdown",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["check"] == "check_source_registry_state"
    assert payload["ok"] is True
    assert payload["doc_id"] == "DAR-I-091"
    assert payload["registry_state"] == "temporary_indexed"


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


def test_refresh_latest_source_temporarily_ingests_newest_markdown_documents(tmp_path: Path) -> None:
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

    source_root = tmp_path / "source-docs"
    source_root.mkdir(parents=True, exist_ok=True)
    doc_089 = source_root / "DAR-I-089.md"
    doc_090 = source_root / "DAR-I-090.md"
    listing = source_root / "listing.html"
    doc_089.write_text("# DAR 089\n\nPublic transport.\n", encoding="utf-8")
    doc_090.write_text("# DAR 090\n\nDefense policy.\n", encoding="utf-8")
    listing.write_text(
        (
            "<html><body>"
            f"<a href=\"{doc_089.as_uri()}\">DAR I Serie 089</a>"
            f"<a href=\"{doc_090.as_uri()}\">DAR I Serie 090</a>"
            "</body></html>"
        ),
        encoding="utf-8",
    )

    profile = f"""schema_version: 1
domain_name: Test Latest Archive
domain_slug: test-latest-archive
domain_summary: Test pack.
risk_class: high
operating_mode: accuracy_first
volatility: fast_changing
fact_sensitivity: helpful
exception_density: medium
exact_wording: important
source_families:
  - name: debates
    canonical_source_type: official
    retrieval_unit: section
    persistence_default: on_use
    discovery:
      strategy: html_listing_document_links
      listing_urls:
        - {listing.as_uri()}
      document_format: markdown
      document_id_regex: "(?P<doc_id>DAR-I-\\\\d+)\\\\.md"
      url_must_contain: "DAR-I-"
required_facts:
  - fact_id: period
    prompt: What period applies?
    required_for:
      - case_application
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

    refresh_script = archive_root / "scripts" / "refresh_latest_source.py"
    result = subprocess.run(
        [
            sys.executable,
            str(refresh_script),
            "--archive-root",
            str(archive_root),
            "--source-family",
            "debates",
            "--latest",
            "2",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert len(payload["temporary_ingested"]) == 2

    freshness = json.loads((archive_root / "artifacts" / "state" / "source-freshness.json").read_text(encoding="utf-8"))
    family = freshness["families"]["debates"]
    assert family["newest_discovered_doc_id"] == "DAR-I-090"
    assert family["newest_temporary_doc_id"] == "DAR-I-090"

    registry_text = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted((archive_root / "artifacts" / "registry").glob("*.md"))
    )
    assert "temporary_indexed" in registry_text

    cache_text = (archive_root / "source" / "cache" / "dar-i-090.md").read_text(encoding="utf-8")
    assert "Defense policy." in cache_text
