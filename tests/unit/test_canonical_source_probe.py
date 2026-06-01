from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_probe_module():
    script_path = (
        Path(__file__).resolve().parents[2]
        / "skills"
        / "canonical-source-explorer"
        / "scripts"
        / "probe_source_family.py"
    )
    spec = importlib.util.spec_from_file_location("probe_source_family", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_probe_classifies_rss_feed() -> None:
    module = load_probe_module()
    body = """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0"><channel><title>Feed</title></channel></rss>
"""
    report = module.classify(
        "https://files.diariodarepublica.pt/rss/serie1.xml",
        "https://files.diariodarepublica.pt/rss/serie1.xml",
        200,
        "application/rss+xml",
        body,
    )
    assert report.source_shape == "rss_feed"
    assert report.recommended_acquisition_mode == "sync_registry_then_promote_linked_documents"
    assert report.browser_escalation_allowed is False


def test_probe_classifies_pdf_surface() -> None:
    module = load_probe_module()
    report = module.classify(
        "https://files.diariodarepublica.pt/1s/2026/06/10500/0000300006.pdf",
        "https://files.diariodarepublica.pt/1s/2026/06/10500/0000300006.pdf",
        200,
        "application/pdf",
        "%PDF-1.7",
    )
    assert report.source_shape == "direct_pdf"
    assert report.retrieval_unit == "pdf_page"
    assert report.browser_escalation_allowed is False


def test_probe_classifies_dre_app_shell() -> None:
    module = load_probe_module()
    body = """
<!DOCTYPE html>
<html>
<head>
  <script type='text/javascript'>window.OutSystemsApp = { basePath: '/dr/' };</script>
  <script src="/dr/scripts/OutSystems.js"></script>
  <script src="/dr/scripts/dr.index.js"></script>
</head>
<body>
  <div id="reactContainer"></div>
  <noscript><span>JavaScript is required</span></noscript>
</body>
</html>
"""
    report = module.classify(
        "https://diariodarepublica.pt/dr",
        "https://diariodarepublica.pt/dr",
        200,
        "text/html; charset=utf-8",
        body,
    )
    assert report.source_shape == "app_shell"
    assert report.browser_escalation_allowed is True
    assert "check_files_host_for_rss_or_pdf_surfaces" in report.adjacent_surface_hints


def test_probe_classifies_consolidated_legal_view() -> None:
    module = load_probe_module()
    report = module.classify(
        "https://diariodarepublica.pt/dr/legislacao-consolidada/decreto-lei/1966-34509075-122540651",
        "https://diariodarepublica.pt/dr/legislacao-consolidada/decreto-lei/1966-34509075-122540651",
        200,
        "text/html",
        "<html><body><main>Consolidated law</main></body></html>",
    )
    assert report.source_shape == "consolidated_legal_view"
    assert report.retrieval_unit == "article_or_section"


def test_probe_classifies_detail_page() -> None:
    module = load_probe_module()
    report = module.classify(
        "https://diariodarepublica.pt/dr/detalhe/lei/23-2026-1128264720",
        "https://diariodarepublica.pt/dr/detalhe/lei/23-2026-1128264720",
        200,
        "text/html",
        '<html><body><a href="https://files.diariodarepublica.pt/doc.pdf">pdf</a></body></html>',
    )
    assert report.source_shape == "canonical_detail_page"
    assert "https://files.diariodarepublica.pt/doc.pdf" in report.adjacent_surface_hints
