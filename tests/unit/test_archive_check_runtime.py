from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ledger.archive_checks import (
    build_currentness_bundle,
    check_confirmation_boundary,
    check_coverage_state,
    check_currentness,
    check_expansion_plan,
    check_source_registry_state,
    check_support_hierarchy,
)


def scaffold_archive(tmp_path: Path) -> Path:
    root = Path(__file__).resolve().parents[2]
    archive_root = tmp_path / "archive-index"
    scaffold_archive_script = root / "skills" / "archive-index-builder" / "scripts" / "scaffold_archive_index.py"
    result = subprocess.run(
        [sys.executable, str(scaffold_archive_script), str(archive_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return archive_root


def scaffold_domain_pack(archive_root: Path, profile: str) -> None:
    root = Path(__file__).resolve().parents[2]
    scaffold_pack_script = root / "skills" / "domain-archive-pack-builder" / "scripts" / "scaffold_domain_pack.py"
    profile_path = archive_root / "recipes" / "domain-profile.yaml"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(profile, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(scaffold_pack_script), str(archive_root), "--profile", str(profile_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


PROFILE_YAML = """schema_version: 1
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


def test_archive_check_runtime_support_hierarchy_uses_package_seam(tmp_path: Path) -> None:
    archive_root = scaffold_archive(tmp_path)
    scaffold_domain_pack(archive_root, PROFILE_YAML)
    (archive_root / "index").mkdir(parents=True, exist_ok=True)
    (archive_root / "index" / "documents.jsonl").write_text(
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

    payload = check_support_hierarchy(
        archive_root,
        {"claims": [{"claim_id": "c1", "decisive": True, "evidence_ids": ["art-43"]}]},
    )

    assert payload["ok"] is True
    assert payload["check"] == "check_support_hierarchy"
    assert payload["counts"]["claims_checked"] == 1


def test_archive_check_runtime_coverage_state_uses_package_seam(tmp_path: Path) -> None:
    archive_root = scaffold_archive(tmp_path)
    scaffold_domain_pack(archive_root, PROFILE_YAML)
    (archive_root / "domain" / "coverage-ledger.yaml").write_text(
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
  - Suggested provisional_weak_slices entry keys: topic, labels, task_types, suspected_support_gap, current_support, reason, source_family, artifact_ids, notes.
  - Suggested support_gaps entry keys: topic, labels, task_types, required_support, current_support, quality_status, follow_up_action, source_family, artifact_ids, notes.
""",
        encoding="utf-8",
    )

    payload = check_coverage_state(archive_root, "resident gains article 43", "rule_lookup")

    assert payload["ok"] is False
    assert payload["status"] == "known_below_target"
    assert payload["suggested_action"] == "expand"


def test_archive_check_runtime_currentness_and_registry_use_package_seam(tmp_path: Path) -> None:
    archive_root = scaffold_archive(tmp_path)
    scaffold_domain_pack(archive_root, PROFILE_YAML)
    artifact_path = archive_root / "artifacts" / "extracts" / "ext-test-currentness.md"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        """---
artifact_type: extract
artifact_id: ext-test-currentness
source_system: diariodarepublica.pt
source_url: https://example.com/current
source_document_id: '34509075'
title: Test currentness extract
verified_at: 2026-06-01
confidence: high
---
# Test currentness extract
""",
        encoding="utf-8",
    )
    (archive_root / "artifacts" / "state" / "source-freshness.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "families": {
                    "statutes": {
                        "last_listing_sync_at": "2026-06-01T16:09:00Z",
                        "last_sync_ok": True,
                        "newest_discovered_doc_id": "34509075",
                        "newest_temporary_doc_id": "34509075",
                        "newest_durable_doc_id": "34509075",
                    },
                    "parliamentary_debates": {
                        "last_listing_sync_at": "2026-06-01T14:25:22Z",
                        "last_sync_ok": True,
                        "newest_discovered_doc_id": "DAR-I-091",
                        "newest_temporary_doc_id": "DAR-I-091",
                        "newest_durable_doc_id": "DAR-I-091",
                    },
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (archive_root / "index").mkdir(parents=True, exist_ok=True)
    (archive_root / "index" / "documents.jsonl").write_text(
        json.dumps(
            {
                "artifact_id": "ext-test-currentness",
                "artifact_type": "extract",
                "path": str(artifact_path),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    cache_file = archive_root / "source" / "cache" / "DAR-I-091.pdf"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("pdf-bytes-placeholder", encoding="utf-8")
    page_index = archive_root / "source" / "index" / "pdf-pages" / "DAR-I-091.jsonl"
    page_index.parent.mkdir(parents=True, exist_ok=True)
    page_index.write_text('{"page": 1, "text": "example"}\n', encoding="utf-8")
    extracted_md = archive_root / "source" / "extracted" / "DAR-I-091.extracted.md"
    extracted_md.parent.mkdir(parents=True, exist_ok=True)
    extracted_md.write_text("# Extracted\n", encoding="utf-8")
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
    built = build_currentness_bundle(
        archive_root,
        "ext-test-currentness",
        "rule_lookup",
        "statutes",
        None,
        None,
        None,
        None,
    )
    currentness_payload = check_currentness(archive_root, built["currentness"])
    registry_payload = check_source_registry_state(
        archive_root,
        "parliamentary_debates",
        None,
        "newest_temporary",
        "temporary_indexed",
        True,
        True,
        True,
    )

    assert built["currentness"]["status"] == "current"
    assert currentness_payload["ok"] is True
    assert registry_payload["ok"] is True
    assert registry_payload["doc_id"] == "DAR-I-091"


def test_archive_check_runtime_accepts_mapping_question_shape_policies(tmp_path: Path) -> None:
    archive_root = scaffold_archive(tmp_path)
    scaffold_domain_pack(archive_root, PROFILE_YAML)
    acquisition_path = archive_root / "recipes" / "source-acquisition.yaml"
    acquisition_path.write_text(
        """schema_version: 1
allowed_source_families:
  - statutes
question_shape_policies:
  rule_lookup:
    allowed_source_families:
      - statutes
    bounded_search:
      initial_query_budget: 2
      refinement_query_budget: 1
      allow_second_stage_refinement: true
skip_persist_reasons:
  - informational_probe
""",
        encoding="utf-8",
    )
    payload = check_expansion_plan(
        archive_root,
        {
            "task_type": "rule_lookup",
            "question_shape": "rule_lookup",
            "source_family": "statutes",
            "source_url": "https://example.com/rule",
            "unit_type": "article",
            "materialize_as": "extract",
            "persistence_action": "persist",
            "search_stage": "initial",
            "query_terms": ["article 43", "resident gains"],
            "reason": "need stronger local support",
        },
    )

    assert payload["ok"] is True
    assert payload["check"] == "check_expansion_plan"


def test_archive_check_runtime_confirmation_boundary_uses_package_seam(tmp_path: Path) -> None:
    archive_root = scaffold_archive(tmp_path)
    scaffold_domain_pack(archive_root, PROFILE_YAML)
    (archive_root / "recipes" / "confirmation-thresholds.yaml").write_text(
        """schema_version: 1
allowed_conclusion_levels:
  - provisional_from_archive
  - confirmed_from_provided_facts
blocking_fact_ids:
  - residency
confirmed_requires_all_blocking_facts: true
forbidden_phrases_when_blocking_facts_missing:
  - definitely
""",
        encoding="utf-8",
    )

    payload = check_confirmation_boundary(
        archive_root,
        {
            "conclusion_level": "confirmed_from_provided_facts",
            "blocking_facts_confirmed": [],
            "blocking_facts_missing": ["residency"],
            "phrasing": "This is definitely confirmed.",
        },
    )

    assert payload["ok"] is False
    assert payload["check"] == "check_confirmation_boundary"
    assert payload["counts"]["failures"] >= 1
