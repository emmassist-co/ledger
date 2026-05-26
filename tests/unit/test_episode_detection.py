from __future__ import annotations

from parliament.models.document import ExtractedDocument, ExtractedPage
from parliament.pipeline.stages.detect_episodes import detect_episodes


def test_detect_episodes_avoids_duplicate_episode_from_large_section_split() -> None:
    extraction = ExtractedDocument(
        document_id="DAR-I-TEST",
        pages=[
            ExtractedPage(
                document_id="DAR-I-TEST",
                page_number=1,
                markdown="## SUMÁRIO\nResumo.",
            ),
            ExtractedPage(
                document_id="DAR-I-TEST",
                page_number=2,
                markdown="SESSÃO SOLENE\n" + ("Texto longo. " * 4000),
            ),
        ],
        full_markdown="",
    )

    episodes = detect_episodes(extraction, max_section_chars=800)

    solemn_episodes = [episode for episode in episodes if episode.episode_type == "solemn_session"]
    assert len(solemn_episodes) == 1


def test_detect_episodes_titles_pcp_declaration_block_from_generic_marker() -> None:
    extraction = ExtractedDocument(
        document_id="DAR-I-TEST",
        pages=[
            ExtractedPage(
                document_id="DAR-I-TEST",
                page_number=7,
                markdown=(
                    "Tem a palavra, para a primeira declaração política, a Sr.ª Deputada Paula Santos.\n"
                    "A Sr.ª **Paula Santos** (PCP): — Na jornada de luta do 1.º de Maio..."
                ),
            ),
            ExtractedPage(
                document_id="DAR-I-TEST",
                page_number=8,
                markdown="A Sr.ª **Paula Santos** (PCP): — O custo de vida aumentou.",
            ),
            ExtractedPage(
                document_id="DAR-I-TEST",
                page_number=9,
                markdown="O Sr. **João Antunes dos Santos** (PSD): — Pedido de esclarecimento.",
            ),
        ],
        full_markdown="",
    )

    episodes = detect_episodes(extraction, max_section_chars=12_000)

    assert any(episode.title == "PCP labour cost of living" for episode in episodes)


def test_detect_episodes_does_not_split_same_block_on_generic_declaration_page() -> None:
    extraction = ExtractedDocument(
        document_id="DAR-I-TEST",
        pages=[
            ExtractedPage(
                document_id="DAR-I-TEST",
                page_number=15,
                markdown=(
                    "É uma vergonha, a posição do Partido Comunista Português.\n"
                    "O Sr. **Paulo Núncio** (CDS-PP): — ...\n"
                    "O Sr. **Presidente** (Diogo Pacheco de Amorim): — Tem a palavra a Sr.ª Deputada Inês de Sousa Real."
                ),
            ),
            ExtractedPage(
                document_id="DAR-I-TEST",
                page_number=16,
                markdown="A Sr.ª **Paula Santos** (PCP): — Nós defendemos a paz.",
            ),
            ExtractedPage(
                document_id="DAR-I-TEST",
                page_number=17,
                markdown=(
                    "O Sr. **Presidente** (Diogo Pacheco de Amorim): — Tem agora a palavra, para uma declaração política, o Sr. Deputado Paulo Núncio.\n"
                    "O Sr. Deputado Paulo Núncio (CDS-PP): — A reforma laboral é essencial."
                ),
            ),
        ],
        full_markdown="",
    )

    episodes = detect_episodes(extraction, max_section_chars=12_000)

    assert len(episodes) == 2
    assert episodes[0].title != "Partido"
    assert episodes[1].title == "CDS labour reform"
