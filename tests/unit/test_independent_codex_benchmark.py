from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module():
    root = Path(__file__).resolve().parents[2]
    path = root / "skills" / "archive-evals" / "scripts" / "benchmark_independent_codex.py"
    spec = importlib.util.spec_from_file_location("benchmark_independent_codex", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_benchmark_markdown_extracts_questions() -> None:
    mod = load_module()
    root = Path(__file__).resolve().parents[2]
    benchmark = root / "docs" / "evals" / "2026-05-28-dr-only-edge-case-portuguese-legal-benchmark.md"
    questions = mod.parse_benchmark_markdown(benchmark)

    assert len(questions) == 12
    assert questions[0].question_id == "PT-DR-EDGE-001"
    assert "despesas adicionais" in questions[0].question
    assert len(questions[0].must_hit_points) >= 3
    assert questions[0].source_urls


def test_summarize_grades_aggregates_verdicts_and_source_discipline(tmp_path: Path) -> None:
    mod = load_module()
    benchmark = tmp_path / "benchmark.md"
    benchmark.write_text(
        """# Demo

### Q1
- Question: `Pergunta 1`
- Expected answer:
  resposta 1
- Must-hit points:
  - ponto 1
- DR source:
  - [Fonte](https://diariodarepublica.pt/dr/x)

### Q2
- Question: `Pergunta 2`
- Expected answer:
  resposta 2
- Must-hit points:
  - ponto 2
- DR source:
  - [Fonte](https://diariodarepublica.pt/dr/y)
""",
        encoding="utf-8",
    )
    questions = mod.parse_benchmark_markdown(benchmark)

    answers_dir = tmp_path / "answers"
    grades_dir = tmp_path / "grades"
    answers_dir.mkdir()
    grades_dir.mkdir()

    (answers_dir / "Q1.json").write_text(
        json.dumps({"support_status": "extract", "source_urls": ["https://diariodarepublica.pt/dr/x"]}),
        encoding="utf-8",
    )
    (answers_dir / "Q2.json").write_text(
        json.dumps({"support_status": "extract", "source_urls": ["https://example.com/nope"]}),
        encoding="utf-8",
    )
    (grades_dir / "Q1.json").write_text(
        json.dumps({"verdict": "pass", "used_only_allowed_sources": True}),
        encoding="utf-8",
    )
    (grades_dir / "Q2.json").write_text(
        json.dumps({"verdict": "partial", "used_only_allowed_sources": False}),
        encoding="utf-8",
    )

    summary = mod.summarize_grades(benchmark, questions, answers_dir, grades_dir)
    assert summary["question_count"] == 2
    assert summary["verdict_counts"]["pass"] == 1
    assert summary["verdict_counts"]["partial"] == 1
    assert summary["pass_rate"] == 0.5
    assert summary["pass_or_partial_rate"] == 1.0
    assert summary["source_discipline_rate"] == 0.5
