from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_run_archive_evals_reports_suite_health_and_prune_candidates(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    scaffold_archive = root / "skills" / "archive-index-builder" / "scripts" / "scaffold_archive_index.py"
    run_evals = root / "skills" / "archive-evals" / "scripts" / "run_archive_evals.py"
    archive_root = tmp_path / "archive-index"

    result = subprocess.run(
        [sys.executable, str(scaffold_archive), str(archive_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    (archive_root / "recipes").mkdir(parents=True, exist_ok=True)
    (archive_root / "recipes" / "source-acquisition.yaml").write_text(
        "\n".join(
            [
                "question_shape_policies:",
                "  rule_lookup:",
                "    bounded_search:",
                "      initial_query_budget: 3",
                "      refinement_query_budget: 2",
                "      allow_second_stage_refinement: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    documents_path = archive_root / "index" / "documents.jsonl"
    documents_path.parent.mkdir(parents=True, exist_ok=True)
    documents_path.write_text(
        json.dumps(
            {
                "artifact_id": "art-1",
                "title": "Article 1",
                "artifact_type": "extract",
                "search_text": "article 1 threshold rule",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    scenario = {
        "id": "golden-article-1",
        "bucket": "retrieval",
        "source_kind": "production_derived",
        "query": "article 1 threshold rule",
        "prompt": "What does the archive know about Article 1?",
        "expected_artifacts": ["art-1"],
        "expected_constraints": {
            "require_any_artifact_match": True,
            "require_extract_evidence": False,
            "policy_action": "answer",
            "coverage_term": "Article 1",
        },
        "verifier_checks": ["check_coverage", "check_policy"],
        "case_metadata": {
            "tier": "golden",
            "criticality": "critical",
            "critical_path": True,
            "origin": "production_derived",
            "failure_class": "weak_local_support",
            "stale_after_days": 30,
            "added_at": "2020-01-01",
            "last_failed_at": "2020-01-01",
        },
    }
    scenarios_dir = archive_root / "archive-evals" / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    (scenarios_dir / "golden-article-1.json").write_text(
        json.dumps(scenario, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(run_evals), "run", str(archive_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    report = json.loads((archive_root / "archive-evals" / "reports" / "latest.json").read_text())
    summary = report["summary"]
    assert summary["suite_health"]["golden_case_count"] == 1
    assert summary["suite_health"]["golden_pass_rate"] == 1.0
    assert summary["suite_health"]["critical_path_pass_rate"] == 1.0
    assert summary["suite_health"]["origins"]["production_derived"] == 1
    assert summary["prune_candidates"]["scenario_count"] == 1
    assert summary["prune_candidates"]["candidates"][0]["id"] == "golden-article-1"
    assert any("pruning" in step.lower() for step in summary["recommended_hardening_steps"])


def test_run_archive_evals_reports_expand_mode_source_and_query_failures(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    scaffold_archive = root / "skills" / "archive-index-builder" / "scripts" / "scaffold_archive_index.py"
    run_evals = root / "skills" / "archive-evals" / "scripts" / "run_archive_evals.py"
    archive_root = tmp_path / "archive-index"

    result = subprocess.run(
        [sys.executable, str(scaffold_archive), str(archive_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    (archive_root / "recipes").mkdir(parents=True, exist_ok=True)
    (archive_root / "recipes" / "source-acquisition.yaml").write_text(
        "\n".join(
            [
                "question_shape_policies:",
                "  rule_lookup:",
                "    bounded_search:",
                "      initial_query_budget: 3",
                "      refinement_query_budget: 2",
                "      allow_second_stage_refinement: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    documents_path = archive_root / "index" / "documents.jsonl"
    documents_path.parent.mkdir(parents=True, exist_ok=True)
    documents = [
        {
            "artifact_id": "art-dr",
            "title": "Artigo 877 do Codigo Civil",
            "artifact_type": "article_block",
            "source_system": "diariodarepublica.pt",
            "source_url": "https://diariodarepublica.pt/dr/example-877",
            "search_text": "codigo civil artigo 877 venda filho anulavel",
        },
        {
            "artifact_id": "art-at",
            "title": "FAQ tornas IRS",
            "artifact_type": "extract",
            "source_system": "info.portaldasfinancas.gov.pt",
            "source_url": "https://info.portaldasfinancas.gov.pt/example-tornas",
            "search_text": "tornas irs faq mais valias",
        },
        {
            "artifact_id": "art-dr-overbudget",
            "title": "Artigo 1296 do Codigo Civil",
            "artifact_type": "article_block",
            "source_system": "diariodarepublica.pt",
            "source_url": "https://diariodarepublica.pt/dr/example-1296",
            "search_text": "codigo civil artigo 1296 usucapiao posse registo",
        },
    ]
    documents_path.write_text(
        "\n".join(json.dumps(doc) for doc in documents) + "\n",
        encoding="utf-8",
    )

    base_expectations = {
        "response_mode": "expand_then_answer",
        "expected_decision_action": "expand",
        "run_mode": "expand_mode_primary",
        "allowed_source_systems": ["diariodarepublica.pt"],
    }
    base_metadata = {
        "tier": "golden",
        "criticality": "high",
        "critical_path": True,
        "origin": "user_seeded",
        "failure_class": "bounded_canonical_expansion",
    }
    scenarios = [
        {
            "id": "expand-dr-pass",
            "bucket": "grounding",
            "source_kind": "user_seeded",
            "query": "codigo civil artigo 877 venda filho anulavel",
            "prompt": "O artigo 877 permite a anulacao da venda a filho?",
            "expected_artifacts": ["art-dr"],
            "expected_constraints": {
                "require_any_artifact_match": True,
                "require_extract_evidence": False,
                "policy_action": "expand",
                "coverage_term": "artigo 877",
            },
            "verifier_checks": ["check_policy"],
            "trajectory_expectations": {
                "decision_record": {
                    "action": "expand",
                    "reason": "Need canonical article support.",
                    "quality_status": "insufficient_local_support",
                    "question_shape": "rule_lookup",
                    "search_stage": "initial",
                    "query_terms": ["codigo civil artigo 877", "venda a filhos anulavel"],
                    "persistence_action": "persist",
                }
            },
            "answer_expectations": base_expectations,
            "case_metadata": base_metadata,
        },
        {
            "id": "expand-wrong-source",
            "bucket": "grounding",
            "source_kind": "user_seeded",
            "query": "tornas irs faq mais valias",
            "prompt": "As tornas contam para IRS?",
            "expected_artifacts": ["art-at"],
            "expected_constraints": {
                "require_any_artifact_match": True,
                "require_extract_evidence": False,
                "policy_action": "expand",
                "coverage_term": "tornas irs",
            },
            "verifier_checks": ["check_policy"],
            "trajectory_expectations": {
                "decision_record": {
                    "action": "expand",
                    "reason": "Need canonical support.",
                    "quality_status": "insufficient_local_support",
                    "question_shape": "rule_lookup",
                    "search_stage": "initial",
                    "query_terms": ["tornas irs faq"],
                    "persistence_action": "persist",
                }
            },
            "answer_expectations": base_expectations,
            "case_metadata": base_metadata,
        },
        {
            "id": "expand-overbudget-refinement",
            "bucket": "grounding",
            "source_kind": "user_seeded",
            "query": "codigo civil artigo 1296 usucapiao posse registo",
            "prompt": "Qual e o prazo geral da usucapiao?",
            "expected_artifacts": ["art-dr-overbudget"],
            "expected_constraints": {
                "require_any_artifact_match": True,
                "require_extract_evidence": False,
                "policy_action": "expand",
                "coverage_term": "artigo 1296",
            },
            "verifier_checks": ["check_policy"],
            "trajectory_expectations": {
                "decision_record": {
                    "action": "expand",
                    "reason": "Need refined canonical search.",
                    "quality_status": "insufficient_local_support",
                    "question_shape": "rule_lookup",
                    "search_stage": "refinement",
                    "query_terms": [
                        "codigo civil artigo 1296",
                        "usucapiao posse sem registo",
                        "prazo geral usucapiao",
                    ],
                    "persistence_action": "persist",
                }
            },
            "answer_expectations": base_expectations,
            "case_metadata": base_metadata,
        },
    ]

    scenarios_dir = archive_root / "archive-evals" / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    for scenario in scenarios:
        (scenarios_dir / f"{scenario['id']}.json").write_text(
            json.dumps(scenario, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )

    result = subprocess.run(
        [sys.executable, str(run_evals), "run", str(archive_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    report = json.loads((archive_root / "archive-evals" / "reports" / "latest.json").read_text())
    summary = report["summary"]
    expand = summary["expand_mode_metrics"]
    assert expand["scenario_count"] == 3
    assert expand["expand_success_rate"] == 0.333333
    assert expand["answer_pass_rate_after_expand"] == 1.0
    assert expand["persistence_success_rate"] == 0.333333
    assert expand["wrong_source_rate"] == 0.333333
    assert expand["query_efficiency_failure_rate"] == 0.333333
    assert expand["bounded_failure_rate"] == 0.0
    assert any("source-family enforcement" in step for step in summary["recommended_hardening_steps"])
    assert any("search templates" in step for step in summary["recommended_hardening_steps"])
