from __future__ import annotations

from dataclasses import dataclass
import re

from ledger.archive_index.artifacts import write_archive_artifact
from ledger.archive_index.navigation import rebuild_navigation_index
from ledger.archive_index.paths import ArchiveIndexPaths
from ledger.dr.client import DrConsolidatedDocument, DrLegislationDetail


@dataclass(frozen=True)
class TaxVerticalBuildResult:
    act_count: int
    article_block_count: int
    consolidation_note_count: int


def build_tax_vertical(
    *,
    paths: ArchiveIndexPaths,
    anchor_id: str,
    act_detail: DrLegislationDetail,
    consolidated_document: DrConsolidatedDocument,
) -> TaxVerticalBuildResult:
    corpus = paths.corpus("dr")

    write_archive_artifact(
        path=corpus.artifact_path("act", f"act-{anchor_id}"),
        frontmatter={
            "artifact_type": "act",
            "artifact_id": f"act-{anchor_id}",
            "source_system": "diariodarepublica.pt",
            "source_url": act_detail.source_url,
            "source_title": act_detail.source_title,
            "source_document_id": act_detail.source_document_id,
            "publication_text": act_detail.publication_text,
            "number": act_detail.number,
            "normalized_type": act_detail.normalized_type,
            "consolidated_url": consolidated_document.source_url,
            "eli_html_url": consolidated_document.eli_html_url,
            "eli_pdf_url": consolidated_document.eli_pdf_url,
            "confidence": "high",
            "linked_ids": [],
        },
        body="\n".join(
            [
                f"# {act_detail.source_title}",
                "",
                act_detail.summary,
                "",
                f"- Publication: {act_detail.publication_text}",
                f"- Consolidated source: {consolidated_document.source_url}",
                f"- ELI HTML: {consolidated_document.eli_html_url}",
                f"- ELI PDF: {consolidated_document.eli_pdf_url}",
                "",
            ]
        ),
    )

    promoted_articles = []
    for article in consolidated_document.articles:
        slug = _slug_article_number(article.number)
        artifact_id = f"art-{anchor_id}-{slug}"
        promoted_articles.append(artifact_id)
        write_archive_artifact(
            path=corpus.artifact_path("article_block", artifact_id),
            frontmatter={
                "artifact_type": "article_block",
                "artifact_id": artifact_id,
                "source_system": "diariodarepublica.pt",
                "source_url": consolidated_document.source_url,
                "eli_html_url": consolidated_document.eli_html_url,
                "eli_pdf_url": consolidated_document.eli_pdf_url,
                "article_number": article.number,
                "confidence": "high",
                "linked_ids": [f"act-{anchor_id}"],
            },
            body="\n".join([f"# {article.heading or f'Artigo {article.number}'}", "", article.text, ""]),
        )

    write_archive_artifact(
        path=corpus.artifact_path("consolidation_note", f"note-{anchor_id}-capital-gains"),
        frontmatter={
            "artifact_type": "consolidation_note",
            "artifact_id": f"note-{anchor_id}-capital-gains",
            "source_system": "diariodarepublica.pt",
            "source_url": consolidated_document.source_url,
            "eli_html_url": consolidated_document.eli_html_url,
            "eli_pdf_url": consolidated_document.eli_pdf_url,
            "confidence": "medium",
            "linked_ids": [f"act-{anchor_id}", *promoted_articles],
        },
        body="\n".join(
            [
                "# Capital gains note",
                "",
                "This note ties the general IRC treatment of capital gains to the participation-exemption provision when its legal requirements are met.",
                "",
                consolidated_document.note,
                "",
            ]
        ),
    )

    rebuild_navigation_index(paths)
    return TaxVerticalBuildResult(act_count=1, article_block_count=len(promoted_articles), consolidation_note_count=1)


def _slug_article_number(article_number: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", article_number.lower()).strip("-")
