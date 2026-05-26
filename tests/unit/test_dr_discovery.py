from __future__ import annotations

from pathlib import Path

from ledger.dr.discovery import (
    discover_acts_from_search_hits,
    discover_recent_acts,
    parse_act_detail,
    parse_legislation_by_date,
)


def test_parse_legislation_by_date_extracts_observed_metadata(tmp_path: Path) -> None:
    fixture = Path("tests/fixtures/dr/legislacao-por-data.html").read_text()

    acts = parse_legislation_by_date(fixture, base_url="https://diariodarepublica.pt")

    assert len(acts) == 2
    first = acts[0]
    assert first.source_url == "https://diariodarepublica.pt/dr/detalhe/parlamento/13-2023-211340863"
    assert first.source_document_id == "211340863"
    assert first.source_title == "Lei n.º 13/2023, de 3 de abril"
    assert first.normalized_date == "2023-04-03"
    assert first.observed_facets["tema"] == ["Trabalho e emprego"]
    assert first.observed_facets["codigo"] == ["Código do Trabalho"]


def test_parse_act_detail_keeps_canonical_links_and_observed_facets() -> None:
    fixture = Path("tests/fixtures/dr/act-detail.html").read_text()

    detail = parse_act_detail(fixture, source_url="https://diariodarepublica.pt/dr/detalhe/parlamento/13-2023-211340863")

    assert detail.source_title == "Lei n.º 13/2023, de 3 de abril"
    assert detail.normalized_type == "lei"
    assert detail.observed_facets["codigo"] == ["Código do Trabalho"]
    assert detail.related_links["consolidada"] == "https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2023-211366691"


def test_discover_recent_acts_combines_listing_and_detail_without_inferred_fields() -> None:
    listing_html = Path("tests/fixtures/dr/legislacao-por-data.html").read_text()
    detail_html = Path("tests/fixtures/dr/act-detail.html").read_text()

    def fetch(url: str) -> str:
        if "detalhe/parlamento/13-2023-211340863" in url:
            return detail_html
        raise AssertionError(f"unexpected url: {url}")

    discovered = discover_recent_acts(
        listing_html=listing_html,
        fetch_detail_html=fetch,
        base_url="https://diariodarepublica.pt",
        max_acts=1,
    )

    assert len(discovered) == 1
    first = discovered[0]
    assert first.source_title == "Lei n.º 13/2023, de 3 de abril"
    assert first.related_links["consolidada"].endswith("2023-211366691")
    assert first.observed_facets["tema"] == ["Trabalho e emprego"]
    assert not first.inferred_metadata


def test_discover_acts_from_search_hits_builds_registry_ready_records() -> None:
    hits = [
        {
            "_source": {
                "dbId": 901693497,
                "fileId": 901693408,
                "title": "Despacho n.º 40/2025  - Diário da República n.º 1/2025, Série II de 2025-01-02",
                "tipo": "Despacho",
                "numero": "40/2025",
                "ano": "2025",
                "dataPublicacao": "2025-01-02",
                "serie": "II",
                "tipoConteudo": "DiplomaLegis",
                "docType": "LEGISLACAO",
                "sumario": "<p>Define as regras de inscrição nos cuidados de saúde primários.</p>",
            }
        }
    ]

    discovered = discover_acts_from_search_hits(hits=hits, base_url="https://diariodarepublica.pt")

    assert len(discovered) == 1
    first = discovered[0]
    assert first.source_document_id == "901693497"
    assert first.source_url == "https://diariodarepublica.pt/dr/detalhe/despacho/40-2025-901693497"
    assert first.normalized_type == "despacho"
    assert first.summary == "Define as regras de inscrição nos cuidados de saúde primários."
    assert first.observed_facets["serie"] == ["II"]
    assert first.inferred_metadata["file_id"] == "901693408"
