from __future__ import annotations

from pathlib import Path

def test_repo_local_skills_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    expected = [
        "skills/archive-index-builder/SKILL.md",
        "skills/archive-evals/SKILL.md",
        "skills/archive-operator/SKILL.md",
        "skills/domain-archive-pack-builder/SKILL.md",
    ]

    for relative_path in expected:
        assert (root / relative_path).exists(), relative_path


def test_archive_eval_scripts_exist() -> None:
    root = Path(__file__).resolve().parents[2]

    assert (root / "skills" / "archive-evals" / "scripts" / "run_archive_evals.py").exists()
    assert (root / "skills" / "archive-evals" / "scripts" / "scaffold_archive_evals.py").exists()
    assert (root / "skills" / "domain-archive-pack-builder" / "scripts" / "scaffold_domain_pack.py").exists()
    assert (root / "skills" / "domain-archive-pack-builder" / "scripts" / "validate_domain_pack.py").exists()
    assert (root / "skills" / "domain-archive-pack-builder" / "scripts" / "check_expansion_plan.py").exists()
    assert (root / "skills" / "domain-archive-pack-builder" / "scripts" / "check_support_hierarchy.py").exists()
    assert (root / "skills" / "domain-archive-pack-builder" / "scripts" / "check_confirmation_boundary.py").exists()
    assert (root / "skills" / "domain-archive-pack-builder" / "scripts" / "benchmark_domain_pack.py").exists()


def test_readme_mentions_archive_commands() -> None:
    root = Path(__file__).resolve().parents[2]
    readme = (root / "README.md").read_text()

    assert "ledger archive scaffold" in readme
    assert "ledger eval run" in readme
