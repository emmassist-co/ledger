from __future__ import annotations

import json
from pathlib import Path

from ledger.explorer import build_explorer_html, build_explorer_payload
from ledger.io.paths import DocumentPaths
from ledger.io.writers import write_text_file


def _write_markdown(path: Path, frontmatter: str, body: str) -> None:
    write_text_file(path, f"---\n{frontmatter}\n---\n\n{body.strip()}\n")


def test_build_explorer_payload_reads_artifacts_and_counts(tmp_path: Path) -> None:
    paths = DocumentPaths.from_root(tmp_path, "DAR-I-TEST")
    write_text_file(paths.document_root / "metadata.json", json.dumps({"document_id": "DAR-I-TEST", "page_count": 20}))
    write_text_file(paths.source_dir / "DAR-I-TEST.pdf", "fake pdf")
    write_text_file(
        paths.source_dir / "page_map.json",
        json.dumps(
            {
                "document_id": "DAR-I-TEST",
                "pages": [
                    {"page_number": 7, "text": "Paula Santos afirmou que 10% dos mais ricos detêm 60% da riqueza."},
                    {"page_number": 8, "text": "Outro parágrafo relevante."},
                ],
            }
        ),
    )
    _write_markdown(
        paths.views_dir / "level-1-simple.md",
        "\n".join(
            [
                "document_id: DAR-I-TEST",
                "view_id: level-1-simple",
                "artifact_type: view",
                "level: 1",
                "title: Simple",
            ]
        ),
        "# Simple\n\nResumo",
    )
    _write_markdown(
        paths.episodes_dir / "ep-0001-test.md",
        "\n".join(
            [
                "document_id: DAR-I-TEST",
                "episode_id: ep-0001-test",
                "artifact_type: episode",
                "title: Episode",
                "type: declaration_block",
                "pages: [1, 2]",
            ]
        ),
        "# Episode\n\n## What happened\n\nAlgo aconteceu.",
    )
    _write_markdown(
        paths.claims_dir / "clm-0001-test.md",
        "\n".join(
            [
                "document_id: DAR-I-TEST",
                "claim_id: clm-0001-test",
                "artifact_type: claim",
                "title: Claim",
                "speaker: Paula Santos",
                "party: PCP",
                "episode:",
                "  id: ep-0001-test",
                "  type: episode",
                "  path: ../episodes/ep-0001-test.md",
                "references:",
                "- id: ref-test",
                "  type: reference",
                "  path: ../references/ref-test.md",
            ]
        ),
        "# Claim\n\n## Claim\n\nAfirmação.\n\n## Source mention\n\npp. 7-9",
    )
    _write_markdown(
        paths.references_dir / "ref-test.md",
        "\n".join(
            [
                "document_id: DAR-I-TEST",
                "reference_id: ref-test",
                "artifact_type: reference",
                "title: Reference",
                "name: Reference",
            ]
        ),
        "# Reference\n\nDescrição.",
    )
    _write_markdown(
        paths.document_root / "index.md",
        "\n".join(
            [
                "document_id: DAR-I-TEST",
                "view_id: index",
                "artifact_type: index",
                "title: Índice",
            ]
        ),
        "# Índice\n\nResumo do documento.",
    )

    payload = build_explorer_payload(paths.document_root)

    assert payload["document"]["document_id"] == "DAR-I-TEST"
    assert payload["document"]["source_pdf"] == "source/DAR-I-TEST.pdf"
    assert payload["document"]["pages"][0]["page_number"] == 7
    assert payload["counts"] == {"episodes": 1, "claims": 1, "references": 1, "views": 1}
    assert payload["views"][0]["id"] == "level-1-simple"
    assert payload["episodes"][0]["id"] == "ep-0001-test"
    assert payload["claims"][0]["id"] == "clm-0001-test"
    assert payload["claims"][0]["metadata"]["speaker"] == "Paula Santos"
    assert payload["claims"][0]["metadata"]["source_context"]["page_number"] == 7
    assert payload["references"][0]["id"] == "ref-test"


def test_build_explorer_payload_prefers_claim_matching_context(tmp_path: Path) -> None:
    paths = DocumentPaths.from_root(tmp_path, "DAR-I-TEST")
    write_text_file(paths.document_root / "metadata.json", json.dumps({"document_id": "DAR-I-TEST", "page_count": 20}))
    write_text_file(paths.source_dir / "DAR-I-TEST.pdf", "fake pdf")
    write_text_file(
        paths.source_dir / "page_map.json",
        json.dumps(
            {
                "document_id": "DAR-I-TEST",
                "pages": [
                    {
                        "page_number": 14,
                        "text": "\n".join(
                            [
                                "O que eu acho estranho é que, perante as dificuldades do povo português, venha o Deputado do PSD João Antunes dos Santos e não tenha perguntas. Esse é que é o problema.",
                                "O PCP não reconhece a agressão da Rússia à Ucrânia e escolhe Putin em vez de Zelensky, disse João Antunes dos Santos no debate.",
                            ]
                        ),
                    }
                ],
            }
        ),
    )
    _write_markdown(
        paths.claims_dir / "clm-0005-test.md",
        "\n".join(
            [
                "document_id: DAR-I-TEST",
                "claim_id: clm-0005-test",
                "artifact_type: claim",
                "title: PCP não reconhece a agressão da Rússia à Ucrânia e escolhe Putin em vez de Zelensky.",
                "speaker: João Antunes dos Santos",
                "party: PSD",
            ]
        ),
        "# Claim\n\n## Claim\n\nPCP não reconhece a agressão da Rússia à Ucrânia e escolhe Putin em vez de Zelensky.\n\n## Source mention\n\npp. 13-14",
    )
    _write_markdown(
        paths.document_root / "index.md",
        "\n".join(
            [
                "document_id: DAR-I-TEST",
                "view_id: index",
                "artifact_type: index",
                "title: Índice",
            ]
        ),
        "# Índice",
    )

    payload = build_explorer_payload(paths.document_root)

    assert payload["claims"][0]["metadata"]["source_context"]["page_number"] == 14
    assert "Putin" in payload["claims"][0]["metadata"]["source_context"]["excerpt"]


def test_build_explorer_payload_marks_missing_exact_claim_context(tmp_path: Path) -> None:
    paths = DocumentPaths.from_root(tmp_path, "DAR-I-TEST")
    write_text_file(paths.document_root / "metadata.json", json.dumps({"document_id": "DAR-I-TEST", "page_count": 20}))
    write_text_file(paths.source_dir / "DAR-I-TEST.pdf", "fake pdf")
    write_text_file(
        paths.source_dir / "page_map.json",
        json.dumps(
            {
                "document_id": "DAR-I-TEST",
                "pages": [
                    {
                        "page_number": 14,
                        "text": "O que eu acho estranho é que, perante as dificuldades do povo português, venha o Deputado do PSD João Antunes dos Santos e não tenha perguntas.",
                    }
                ],
            }
        ),
    )
    _write_markdown(
        paths.claims_dir / "clm-0005-test.md",
        "\n".join(
            [
                "document_id: DAR-I-TEST",
                "claim_id: clm-0005-test",
                "artifact_type: claim",
                "title: PCP não reconhece a agressão da Rússia à Ucrânia e escolhe Putin em vez de Zelensky.",
                "speaker: João Antunes dos Santos",
                "party: PSD",
            ]
        ),
        "# Claim\n\n## Claim\n\nPCP não reconhece a agressão da Rússia à Ucrânia e escolhe Putin em vez de Zelensky.\n\n## Source mention\n\npp. 13-14",
    )
    _write_markdown(
        paths.document_root / "index.md",
        "\n".join(
            [
                "document_id: DAR-I-TEST",
                "view_id: index",
                "artifact_type: index",
                "title: Índice",
            ]
        ),
        "# Índice",
    )

    payload = build_explorer_payload(paths.document_root)

    assert payload["claims"][0]["metadata"]["source_context"]["page_number"] == 14
    assert payload["claims"][0]["metadata"]["source_context"]["status"] == "not_found"
    assert payload["claims"][0]["metadata"]["source_context"]["excerpt"] is None


def test_build_explorer_html_embeds_payload_and_shell(tmp_path: Path) -> None:
    payload = {
        "document": {
            "document_id": "DAR-I-TEST",
            "title": "DAR-I-TEST",
            "page_count": 20,
            "source_pdf": "source/DAR-I-TEST.pdf",
            "pages": [{"page_number": 7, "text": "Paula Santos afirmou que 10% dos mais ricos detêm 60% da riqueza."}],
        },
        "counts": {"episodes": 1, "claims": 1, "references": 1, "views": 3},
        "views": [{"id": "level-1-simple", "title": "Simple", "body": "# Simple\n\nclaim clm-0001 and ref-test"}],
        "episodes": [],
        "claims": [{"id": "clm-0001-test", "title": "Claim title", "body": "# Claim"}],
        "references": [{"id": "ref-test", "title": "Reference title", "body": "# Reference"}],
        "index": {"id": "index", "title": "Índice", "body": "# Índice"},
    }

    html = build_explorer_html(payload)

    assert "Ledger Explorer" in html
    assert "level-1-simple" in html
    assert "DAR-I-TEST" in html
    assert "__LEDGER_DATA__" in html
    assert "line-height: 1.72" in html
    assert "navigateToArtifact" in html
    assert "simple-lede" in html
    assert "renderImportantClaimsSection" in html
    assert "renderInlineCitationClusters" in html
    assert "openPdfAtPage" in html
    assert "pdf-frame" in html
    assert "source-context" in html
    assert "shortIdForClaim" in html
    assert "routeForArtifact" in html
    assert "hashchange" in html
    assert "openPdfAtPage(" in html
    assert "resetPdfPreview" in html
    assert "claim-callout" in html
    assert "nav-link.active" in html


def test_build_explorer_html_keeps_canonical_targets_for_short_claim_ids() -> None:
    payload = {
        "document": {"document_id": "DAR-I-TEST", "title": "DAR-I-TEST", "page_count": 20, "source_pdf": "source/DAR-I-TEST.pdf", "pages": []},
        "counts": {"episodes": 0, "claims": 1, "references": 0, "views": 1},
        "views": [
            {
                "id": "level-1-simple",
                "title": "Simple",
                "body": "# Simple\n\n(Fontes: clm-0001)",
            }
        ],
        "episodes": [],
        "claims": [
            {
                "id": "clm-0001-full-claim-id",
                "title": "Claim title",
                "body": "# Claim",
            }
        ],
        "references": [],
        "index": {"id": "index", "title": "Índice", "body": "# Índice"},
    }

    html = build_explorer_html(payload)

    assert "targetId: item.id" in html
    assert "shortIdForClaim(item.id)" in html


def test_build_explorer_html_escapes_quotes_in_artifact_labels() -> None:
    payload = {
        "document": {"document_id": "DAR-I-TEST", "title": "DAR-I-TEST", "page_count": 20, "source_pdf": "source/DAR-I-TEST.pdf", "pages": []},
        "counts": {"episodes": 0, "claims": 1, "references": 0, "views": 1},
        "views": [
            {
                "id": "level-1-simple",
                "title": "Simple",
                "body": '# Simple\n\n(Fontes: PCP sempre esteve do lado da liberdade, democracia, paz e solidariedade e alertou contra a escalada da guerra, propondo diplomacia.)',
            }
        ],
        "episodes": [],
        "claims": [
            {
                "id": "clm-0009-test",
                "title": 'PCP sempre esteve do lado da liberdade, democracia, paz e solidariedade e alertou contra a escalada da guerra, propondo diplomacia.',
                "body": "# Claim",
            }
        ],
        "references": [],
        "index": {"id": "index", "title": "Índice", "body": "# Índice"},
    }

    html = build_explorer_html(payload)

    assert "escapeHtmlAttribute" in html


def test_build_explorer_html_does_not_emit_title_attribute_on_artifact_buttons() -> None:
    payload = {
        "document": {"document_id": "DAR-I-TEST", "title": "DAR-I-TEST", "page_count": 20, "source_pdf": "source/DAR-I-TEST.pdf", "pages": []},
        "counts": {"episodes": 0, "claims": 1, "references": 0, "views": 1},
        "views": [{"id": "level-1-simple", "title": "Simple", "body": "# Simple\n\n(Fontes: clm-0001)"}],
        "episodes": [],
        "claims": [{"id": "clm-0001-full-claim-id", "title": 'Claim "quoted" title', "body": "# Claim"}],
        "references": [],
        "index": {"id": "index", "title": "Índice", "body": "# Índice"},
    }

    html = build_explorer_html(payload)

    assert 'title="${labelAttr}"' not in html


def test_build_explorer_html_skips_self_linking_current_claim() -> None:
    payload = {
        "document": {"document_id": "DAR-I-TEST", "title": "DAR-I-TEST", "page_count": 20, "source_pdf": "source/DAR-I-TEST.pdf", "pages": []},
        "counts": {"episodes": 0, "claims": 1, "references": 0, "views": 1},
        "views": [{"id": "level-1-simple", "title": "Simple", "body": "# Simple"}],
        "episodes": [],
        "claims": [{"id": "clm-0001-test", "title": "Claim title", "body": "# Claim title\n\n## Claim\n\nClaim title"}],
        "references": [],
        "index": {"id": "index", "title": "Índice", "body": "# Índice"},
    }

    html = build_explorer_html(payload)

    assert "currentArtifact" in html
    assert "currentArtifact.kind === kind && currentArtifact.id === targetId" in html


def test_build_explorer_html_includes_episode_claim_section_renderer() -> None:
    payload = {
        "document": {"document_id": "DAR-I-TEST", "title": "DAR-I-TEST", "page_count": 20, "source_pdf": "source/DAR-I-TEST.pdf"},
        "counts": {"episodes": 1, "claims": 1, "references": 0, "views": 1},
        "views": [],
        "episodes": [
            {
                "id": "ep-0001-test",
                "title": "Episode",
                "body": "# Episode\n\n## Important claims\n\n{'claim': 'Afirmou algo.', 'by': 'Paula Santos (PCP)', 'evidence_pointers': 'p. 3'}",
            }
        ],
        "claims": [{"id": "clm-0001-test", "title": "Afirmou algo.", "body": "# Claim"}],
        "references": [],
        "index": {"id": "index", "title": "Índice", "body": "# Índice"},
    }

    html = build_explorer_html(payload)

    assert "renderImportantClaimsSection" in html


def test_build_explorer_html_includes_evidence_pointer_renderer() -> None:
    payload = {
        "document": {"document_id": "DAR-I-TEST", "title": "DAR-I-TEST", "page_count": 20, "source_pdf": "source/DAR-I-TEST.pdf"},
        "counts": {"episodes": 1, "claims": 0, "references": 0, "views": 1},
        "views": [],
        "episodes": [
            {
                "id": "ep-0001-test",
                "title": "Episode",
                "body": "# Episode\n\n## Evidence pointers\n\n- pp. 7-9: Algo aconteceu.\n- Page 11: Outra coisa.",
            }
        ],
        "claims": [],
        "references": [],
        "index": {"id": "index", "title": "Índice", "body": "# Índice"},
    }

    html = build_explorer_html(payload)

    assert "renderEvidencePointersSection" in html
    assert "pdf-link" in html


def test_build_explorer_html_includes_external_references_list_renderer() -> None:
    payload = {
        "document": {"document_id": "DAR-I-TEST", "title": "DAR-I-TEST", "page_count": 20, "source_pdf": "source/DAR-I-TEST.pdf"},
        "counts": {"episodes": 1, "claims": 0, "references": 0, "views": 1},
        "views": [],
        "episodes": [
            {
                "id": "ep-0001-test",
                "title": "Episode",
                "body": "# Episode\n\n## External references to check\n\nRef A; Ref B; Ref C",
            }
        ],
        "claims": [],
        "references": [],
        "index": {"id": "index", "title": "Índice", "body": "# Índice"},
    }

    html = build_explorer_html(payload)

    assert "renderExternalReferencesSection" in html


def test_build_explorer_html_includes_party_positions_renderer() -> None:
    payload = {
        "document": {"document_id": "DAR-I-TEST", "title": "DAR-I-TEST", "page_count": 20, "source_pdf": "source/DAR-I-TEST.pdf"},
        "counts": {"episodes": 1, "claims": 0, "references": 0, "views": 1},
        "views": [],
        "episodes": [
            {
                "id": "ep-0001-test",
                "title": "Episode",
                "body": "# Episode\n\n## Party positions or reactions\n\nPCP: Critica o Governo.; PSD: Critica o PCP.; IL: Defende a Ucrânia.",
            }
        ],
        "claims": [],
        "references": [],
        "index": {"id": "index", "title": "Índice", "body": "# Índice"},
    }

    html = build_explorer_html(payload)

    assert "renderPartyPositionsSection" in html


def test_build_explorer_html_parses_structured_party_positions_blob() -> None:
    payload = {
        "document": {"document_id": "DAR-I-TEST", "title": "DAR-I-TEST", "page_count": 20, "source_pdf": "source/DAR-I-TEST.pdf"},
        "counts": {"episodes": 1, "claims": 0, "references": 0, "views": 1},
        "views": [],
        "episodes": [
            {
                "id": "ep-0001-test",
                "title": "Episode",
                "body": "# Episode\n\n## Party positions or reactions\n\nPCP: {'temas': ['Críticas às celebrações do 1.º de Maio', 'Pacote laboral']}; PSD: {'temas': ['Promoção do PTRR']}",
            }
        ],
        "claims": [],
        "references": [],
        "index": {"id": "index", "title": "Índice", "body": "# Índice"},
    }

    html = build_explorer_html(payload)

    assert "dictItems = [...raw.matchAll" in html
    assert "'temas'" in html


def test_build_explorer_html_includes_claim_metadata_and_source_renderer() -> None:
    payload = {
        "document": {"document_id": "DAR-I-TEST", "title": "DAR-I-TEST", "page_count": 20, "source_pdf": "source/DAR-I-TEST.pdf"},
        "counts": {"episodes": 1, "claims": 1, "references": 1, "views": 1},
        "views": [],
        "episodes": [{"id": "ep-0001-test", "title": "Episode", "body": "# Episode"}],
        "claims": [
            {
                "id": "clm-0001-test",
                "title": "Claim title",
                "body": "# Claim title\n\n## Claim\n\nAfirmação.\n\n## Source mention\n\npp. 7-9",
                "metadata": {
                    "speaker": "Paula Santos",
                    "party": "PCP",
                    "episode": {"id": "ep-0001-test", "type": "episode", "path": "../episodes/ep-0001-test.md"},
                    "references": [{"id": "ref-test", "type": "reference", "path": "../references/ref-test.md"}],
                },
            }
        ],
        "references": [{"id": "ref-test", "title": "Reference title", "body": "# Reference"}],
        "index": {"id": "index", "title": "Índice", "body": "# Índice"},
    }

    html = build_explorer_html(payload)

    assert "renderSourceMentionSection" in html
    assert "buildClaimSourcePreview" in html
    assert "buildClaimStatement" in html
    assert "backlinks" in html
    assert "Attribution" in html
