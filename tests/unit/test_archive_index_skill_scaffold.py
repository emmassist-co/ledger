from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_archive_index_skill_scaffold_creates_expected_files(tmp_path: Path) -> None:
    script = (
        Path(__file__).resolve().parents[2]
        / "skills"
        / "archive-index-builder"
        / "scripts"
        / "scaffold_archive_index.py"
    )
    out_dir = tmp_path / "archive-index"

    result = subprocess.run(
        [sys.executable, str(script), str(out_dir)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (out_dir / "README.md").exists()
    assert (out_dir / "AGENTS.md").exists()
    assert (out_dir / "AUDIT_AGENT.md").exists()
    assert (out_dir / "TESTING.md").exists()
    assert (out_dir / "config" / "index-policy.yaml").exists()
    assert (out_dir / "sql" / "schema.sql").exists()
    assert (out_dir / "docs" / "promotion-rules.md").exists()
    assert (out_dir / "source" / "downloads").is_dir()
    assert (out_dir / "source" / "manifests").is_dir()
    assert (out_dir / "source" / "extracted").is_dir()
    assert (out_dir / "source" / "index").is_dir()
    assert (out_dir / "source" / "discovery").is_dir()
    assert (out_dir / "artifacts" / "registry").is_dir()
    assert (out_dir / "artifacts" / "extracts").is_dir()
    assert (out_dir / "artifacts" / "derived").is_dir()
    assert (out_dir / "scripts" / "probe_source_family.py").exists()
    assert (out_dir / "scripts" / "archive_verifier.py").exists()
    assert (out_dir / "scripts" / "rebuild_index.py").exists()
    assert (out_dir / "scripts" / "check_index_consistency.py").exists()
    assert (out_dir / "scripts" / "run_archive_check.py").exists()

    readme = (out_dir / "README.md").read_text(encoding="utf-8")
    agents = (out_dir / "AGENTS.md").read_text(encoding="utf-8")
    audit = (out_dir / "AUDIT_AGENT.md").read_text(encoding="utf-8")
    testing = (out_dir / "TESTING.md").read_text(encoding="utf-8")
    assert "escalate to a browser only when rendering or interaction is truly required" in readme
    assert "extract with `liteparse`" in readme
    assert "prefer `uv run ledger archive search-pdf ...` style page retrieval over full-document rereads" in readme
    assert "classify work as `rule_lookup` or `case_application`" in readme
    assert "run `uv run python scripts/probe_source_family.py <url> --family <family> --save`" in readme
    assert "or emit to stdout only with `uv run python scripts/probe_source_family.py <url> --json`" in readme
    assert "when subagents are available, delegate isolated discovery, fetch, indexing, or verification tasks" in readme
    assert "require a compact decision record before `expand`, `persist`, or `skip_persist`" in readme
    assert "For an unfamiliar source family, run `scripts/probe_source_family.py <url> --family <family> --save` before broader fetches." in agents
    assert "For public web pages, prefer clean Markdown capture before any browser step." in agents
    assert "extract pages with `liteparse`" in agents
    assert "use page-level search and retrieval before opening the whole PDF" in agents
    assert "save a cheap-first probe report under `source/discovery/` before escalating" in agents
    assert "before `expand`, `persist`, or `skip_persist`, write a compact structured decision record" in agents
    assert "block exact wording unless support is `raw_source` or `extract`" in agents
    assert "for meaningful archive behavior changes, require at least one independent agent-style run" in agents
    assert "When subagents are available, spawn them for bounded archive tasks" in agents
    assert "probe unfamiliar source families before treating a website as a fetch surface" in audit
    assert "the agent treated an app shell or generic landing page as the canonical source surface without probing" in audit
    assert "classify the task as `rule_lookup` or `case_application`" in audit
    assert "when subagents are available, use them for isolated fetch / verification / source-family subtasks" in audit
    assert "the agent used raw HTML or full-PDF rereads where a clean indexed path was available" in audit
    assert "Probes unfamiliar source families before deciding how to fetch them." in testing
    assert "Uses available subagents for bounded parallel work when that reduces serial archive slog." in testing
    assert "Checks coverage before making decisive claims on potentially partial topics." in testing
