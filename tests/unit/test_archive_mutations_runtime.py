from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ledger.archive_mutations import register_provisional_weak_slice, resolve_provisional_weak_slice


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
"""


def scaffold_archive(tmp_path: Path) -> Path:
    root = Path(__file__).resolve().parents[2]
    archive_root = tmp_path / "archive-index"
    scaffold_archive_script = root / "skills" / "archive-index-builder" / "scripts" / "scaffold_archive_index.py"
    scaffold_pack_script = root / "skills" / "domain-archive-pack-builder" / "scripts" / "scaffold_domain_pack.py"
    result = subprocess.run(
        [sys.executable, str(scaffold_archive_script), str(archive_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    profile_path = archive_root / "recipes" / "domain-profile.yaml"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(PROFILE_YAML, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(scaffold_pack_script), str(archive_root), "--profile", str(profile_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return archive_root


def test_archive_mutations_registers_provisional_weak_slice(tmp_path: Path) -> None:
    archive_root = scaffold_archive(tmp_path)
    (archive_root / "index").mkdir(parents=True, exist_ok=True)
    (archive_root / "index" / "documents.jsonl").write_text(
        json.dumps({"artifact_id": "art-cirs-43", "artifact_type": "article_block"}) + "\n",
        encoding="utf-8",
    )

    payload = register_provisional_weak_slice(
        archive_root,
        "resident gains article 43",
        "rule_lookup",
        {
            "action": "expand",
            "quality_status": "below_target",
            "reason": "local article support may omit the decisive exception",
            "artifact_ids": ["art-cirs-43"],
            "source_family": "statutes",
            "match_terms": ["article 43"],
        },
    )

    assert payload["ok"] is True
    assert payload["status"] == "created"
    coverage = (archive_root / "domain" / "coverage-ledger.yaml").read_text(encoding="utf-8")
    assert "resident gains article 43" in coverage


def test_archive_mutations_resolves_provisional_weak_slice_to_support_gap(tmp_path: Path) -> None:
    archive_root = scaffold_archive(tmp_path)
    register_provisional_weak_slice(
        archive_root,
        "resident gains article 43",
        "rule_lookup",
        {
            "action": "expand",
            "quality_status": "below_target",
            "reason": "local article support may omit the decisive exception",
            "source_family": "statutes",
        },
    )

    payload = resolve_provisional_weak_slice(
        archive_root,
        "resident gains article 43",
        "rule_lookup",
        "confirmed",
        {
            "required_support": "extract",
            "current_support": "article_block",
            "follow_up_action": "expand",
            "note": "Confirmed during enrichment review.",
        },
    )

    assert payload["ok"] is True
    assert payload["status"] == "confirmed"
    assert payload["entry"]["required_support"] == "extract"
    coverage = (archive_root / "domain" / "coverage-ledger.yaml").read_text(encoding="utf-8")
    assert "support_gaps:" in coverage
    assert "article_block" in coverage
