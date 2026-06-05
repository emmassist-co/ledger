from __future__ import annotations

import json
from pathlib import Path

from ledger.consultation.runtime import consult_archive


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_consult_archive_returns_decisive_answer_for_grounded_rule_lookup(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive-index"
    write_jsonl(
        archive_root / "index" / "documents.jsonl",
        [
            {
                "artifact_id": "art-vat",
                "title": "VAT deduction rule",
                "artifact_type": "extract",
                "search_text": "vat deduction rule article input tax deductible",
                "path": str(archive_root / "artifacts" / "extracts" / "art-vat.md"),
            }
        ],
    )
    write_json(archive_root / "artifacts" / "state" / "source-freshness.json", {"schema_version": 1, "families": {}})

    result = consult_archive(archive_root, "What is the VAT deduction rule?")

    assert result.payload["question_shape"] == "rule_lookup"
    assert result.payload["support_state"] == "grounded"
    assert result.payload["outcome"] == "decisive_answer"
    assert result.audit_path.exists()
    assert (archive_root / "artifacts" / "state" / "archive-state-summary.json").exists()


def test_consult_archive_returns_ask_user_when_case_application_lacks_required_facts(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive-index"
    write_jsonl(
        archive_root / "index" / "documents.jsonl",
        [
            {
                "artifact_id": "art-cirs",
                "title": "CIRS article 43",
                "artifact_type": "extract",
                "search_text": "capital gains resident taxpayer article 43",
            }
        ],
    )
    write_json(archive_root / "artifacts" / "state" / "source-freshness.json", {"schema_version": 1, "families": {}})
    write_yaml(
        archive_root / "recipes" / "fact-intake.yaml",
        """schema_version: 1
required_facts:
  - fact_id: residency_status
    required_for:
      - case_application
case_application_policy: block_if_missing
""",
    )

    result = consult_archive(archive_root, "Can I use article 43 for my case?")

    assert result.payload["question_shape"] == "case_application"
    assert result.payload["outcome"] == "ask_user"
    assert result.payload["missing_user_facts"] == ["residency_status"]


def test_consult_archive_returns_expand_for_currentness_sensitive_question_without_freshness(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive-index"
    write_jsonl(
        archive_root / "index" / "documents.jsonl",
        [
            {
                "artifact_id": "art-current",
                "title": "Current VAT rule",
                "artifact_type": "extract",
                "search_text": "current vat rule updated article",
            }
        ],
    )
    write_json(archive_root / "artifacts" / "state" / "source-freshness.json", {"schema_version": 1, "families": {}})
    write_yaml(
        archive_root / "recipes" / "currentness-rules.yaml",
        """schema_version: 1
enabled: true
current_question_shapes:
  - rule_lookup
allowed_statuses:
  - current
  - stale
  - superseded
  - unproven
proof_bundle_fields:
  - checked_at
  - canonical_source_url
""",
    )

    result = consult_archive(archive_root, "What is the current VAT rule?")

    assert result.payload["currentness_sensitive"] is True
    assert result.payload["currentness_state"] == "missing"
    assert result.payload["outcome"] == "expand"


def test_consult_archive_requires_specific_support_for_generic_latest_question(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive-index"
    write_jsonl(
        archive_root / "index" / "documents.jsonl",
        [
            {
                "artifact_id": "art-random",
                "title": "Article 43 Threshold Rule",
                "artifact_type": "extract",
                "search_text": "published legal threshold rule extract",
            }
        ],
    )
    write_json(
        archive_root / "artifacts" / "state" / "source-freshness.json",
        {
            "schema_version": 1,
            "families": {
                "statutes": {
                    "last_sync_ok": True,
                }
            },
        },
    )
    write_yaml(
        archive_root / "recipes" / "currentness-rules.yaml",
        """schema_version: 1
enabled: true
current_question_shapes:
  - rule_lookup
allowed_statuses:
  - current
  - stale
  - superseded
  - unproven
proof_bundle_fields:
  - checked_at
  - canonical_source_url
""",
    )

    result = consult_archive(archive_root, "What are the latest laws published today?")

    assert result.payload["currentness_state"] == "available"
    assert result.payload["support_state"] == "none"
    assert result.payload["outcome"] == "expand"
