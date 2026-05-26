from __future__ import annotations

import json
from pathlib import Path

from ledger.archive_index.dr_build import build_dr_outer_map
from ledger.archive_index.paths import ArchiveIndexPaths


def test_build_dr_outer_map_writes_registry_and_facet_artifacts(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive-index"
    listing_html = Path("tests/fixtures/dr/legislacao-por-data.html").read_text()
    detail_html = Path("tests/fixtures/dr/act-detail.html").read_text()

    def fetch(url: str) -> str:
        if "detalhe/parlamento/13-2023-211340863" in url:
            return detail_html
        return detail_html

    result = build_dr_outer_map(
        paths=ArchiveIndexPaths(archive_root),
        listing_html=listing_html,
        fetch_detail_html=fetch,
        base_url="https://diariodarepublica.pt",
        max_acts=2,
    )

    assert result.registry_count == 2
    assert result.facet_count >= 2
    assert (archive_root / "artifacts" / "dr" / "registry" / "reg-dr-211340863.md").exists()
    assert (archive_root / "artifacts" / "dr" / "facets" / "facet-tema-trabalho-e-emprego.md").exists()

    rows = [json.loads(line) for line in (archive_root / "index" / "documents.jsonl").read_text().splitlines()]
    ids = {row["artifact_id"] for row in rows}
    assert "reg-dr-211340863" in ids
    assert "facet-tema-trabalho-e-emprego" in ids
