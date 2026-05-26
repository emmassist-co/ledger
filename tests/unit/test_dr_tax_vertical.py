from __future__ import annotations

from pathlib import Path

from parliament.archive_index.artifacts import read_archive_artifact
from parliament.archive_index.paths import ArchiveIndexPaths
from parliament.dr.client import DrConsolidatedArticle, DrConsolidatedDocument, DrLegislationDetail
from parliament.dr.tax_vertical import build_tax_vertical


def test_build_tax_vertical_promotes_irc_articles_and_consolidation_note(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive-index"
    paths = ArchiveIndexPaths(archive_root)

    result = build_tax_vertical(
        paths=paths,
        anchor_id="irc",
        act_detail=DrLegislationDetail(
            source_url="https://diariodarepublica.pt/dr/detalhe/decreto-lei/442-b-1988-519003",
            source_document_id="519003",
            source_title="Decreto-Lei n.º 442-B/88",
            publication_text="Diário da República n.º 277/1988, 2.º Suplemento, Série I de 1988-11-30",
            number="442-B/88",
            normalized_type="decreto-lei",
            summary="Aprova o Código do Imposto sobre o Rendimento das Pessoas Colectivas (IRC)",
            full_text="Artigo 1.º Aprovação do Código do IRC",
        ),
        consolidated_document=DrConsolidatedDocument(
            source_url="https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2014-64205634",
            title="Código do Imposto sobre o Rendimento das Pessoas Coletivas - CIRC",
            formatted_title="Lei n.º 2/2014 - Diário da República n.º 11/2014, Série I de 2014-01-16",
            note="Esta versão consolidada tem por base a republicação, em anexo à Lei n.º 2/2014.",
            eli_html_url="https://data.dre.pt/eli/lei/2/2014/p/cons/20251230/pt/html",
            eli_pdf_url="https://data.dre.pt/eli/lei/2/2014/p/cons/20251230/pt/pdf",
            articles=[
                DrConsolidatedArticle(
                    number="46",
                    heading="Artigo 46.º",
                    text="Consideram-se mais-valias os ganhos obtidos.",
                ),
                DrConsolidatedArticle(
                    number="51-C",
                    heading="Artigo 51.º-C",
                    text="A participação isenta depende do preenchimento de requisitos.",
                ),
            ],
        ),
    )

    assert result.act_count == 1
    assert result.article_block_count == 2
    assert result.consolidation_note_count == 1
    act_path = archive_root / "artifacts" / "dr" / "acts" / "act-irc.md"
    assert act_path.exists()
    assert (archive_root / "artifacts" / "dr" / "article-blocks" / "art-irc-46.md").exists()
    assert (archive_root / "artifacts" / "dr" / "article-blocks" / "art-irc-51-c.md").exists()
    assert (archive_root / "artifacts" / "dr" / "consolidation-notes" / "note-irc-capital-gains.md").exists()

    act_artifact = read_archive_artifact(act_path)
    assert act_artifact.metadata["source_url"] == "https://diariodarepublica.pt/dr/detalhe/decreto-lei/442-b-1988-519003"
    assert act_artifact.metadata["consolidated_url"] == "https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2014-64205634"
    assert act_artifact.metadata["eli_html_url"] == "https://data.dre.pt/eli/lei/2/2014/p/cons/20251230/pt/html"
    assert act_artifact.metadata["eli_pdf_url"] == "https://data.dre.pt/eli/lei/2/2014/p/cons/20251230/pt/pdf"
