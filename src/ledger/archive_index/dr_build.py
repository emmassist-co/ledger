from __future__ import annotations

from dataclasses import dataclass
import re

from ledger.archive_index.artifacts import write_archive_artifact
from ledger.archive_index.navigation import rebuild_navigation_index
from ledger.archive_index.paths import ArchiveIndexPaths
from ledger.dr.discovery import DiscoveredAct, discover_recent_acts


@dataclass(frozen=True)
class DrOuterMapBuildResult:
    registry_count: int
    facet_count: int


def build_dr_outer_map(
    *,
    paths: ArchiveIndexPaths,
    listing_html: str,
    fetch_detail_html,
    base_url: str,
    max_acts: int | None = None,
) -> DrOuterMapBuildResult:
    discovered = discover_recent_acts(
        listing_html=listing_html,
        fetch_detail_html=fetch_detail_html,
        base_url=base_url,
        max_acts=max_acts,
    )
    return write_dr_outer_map(
        paths=paths,
        discovered=discovered,
        source_parent_url=f"{base_url}/dr/legislacao-por-data",
    )


def write_dr_outer_map(
    *,
    paths: ArchiveIndexPaths,
    discovered: list[DiscoveredAct],
    source_parent_url: str,
) -> DrOuterMapBuildResult:
    corpus = paths.corpus("dr")

    registry_count = 0
    written_facets: set[str] = set()
    for act in discovered:
        artifact_id = f"reg-dr-{act.source_document_id}"
        linked_ids: list[str] = []
        for facet_type, facet_values in act.observed_facets.items():
            for value in facet_values:
                facet_id = _facet_artifact_id(facet_type, value)
                linked_ids.append(facet_id)
                if facet_id in written_facets:
                    continue
                write_archive_artifact(
                    path=corpus.artifact_path("facet", facet_id),
                    frontmatter={
                        "artifact_type": "facet",
                        "artifact_id": facet_id,
                        "facet_type": facet_type,
                        "label": value,
                        "source_system": "diariodarepublica.pt",
                        "confidence": "high",
                        "linked_ids": [],
                    },
                    body=f"# {value}\n\nFacet observed on DR browse/detail pages.\n",
                )
                written_facets.add(facet_id)

        write_archive_artifact(
            path=corpus.artifact_path("registry", artifact_id),
            frontmatter={
                "artifact_type": "registry",
                "artifact_id": artifact_id,
                "schema_version": 1,
                "extraction_method": "dr-recent-outer-map",
                "doc_id": artifact_id.upper(),
                "source_system": "diariodarepublica.pt",
                "source_url": act.source_url,
                "source_parent_url": source_parent_url,
                "source_document_id": act.source_document_id,
                "source_title": act.source_title,
                "source_date_text": act.source_date_text,
                "normalized_date": act.normalized_date,
                "normalized_type": act.normalized_type,
                "discovery_state": "indexed_l0",
                "confidence": "high",
                "linked_ids": linked_ids,
                "observed_facets": act.observed_facets,
                "related_links": act.related_links,
                "inferred_metadata": act.inferred_metadata,
            },
            body="\n".join(
                [
                    f"# {act.source_title}",
                    "",
                    f"- Source URL: {act.source_url}",
                    f"- Date: {act.normalized_date or act.source_date_text}",
                    f"- Summary: {act.summary or ''}",
                    "",
                ]
            ),
        )
        registry_count += 1

    rebuild_navigation_index(paths)
    return DrOuterMapBuildResult(registry_count=registry_count, facet_count=len(written_facets))


def _facet_artifact_id(facet_type: str, value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return f"facet-{facet_type}-{slug}"
