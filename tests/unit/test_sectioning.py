from __future__ import annotations

from parliament.models.document import ExtractedDocument, ExtractedPage
from parliament.sectioning.heuristics import detect_sections


def _sample_extraction() -> ExtractedDocument:
    pages = [
        ExtractedPage(
            document_id="DAR-I-TEST",
            page_number=1,
            markdown=(
                "## SUMÁRIO\n"
                "Sessão solene sobre a Ucrânia.\n"
                "O Sr. Presidente (PSD): — Está aberta a sessão."
            ),
        ),
        ExtractedPage(
            document_id="DAR-I-TEST",
            page_number=2,
            markdown=(
                "## DECLARAÇÃO POLÍTICA DO PCP\n"
                "A Sr.ª Paula Santos (PCP): — O custo de vida aumentou.\n"
                "Aplausos do PCP."
            ),
        ),
        ExtractedPage(
            document_id="DAR-I-TEST",
            page_number=3,
            markdown=(
                "## VOTAÇÃO\n"
                "Submetida à votação, foi aprovada por unanimidade.\n"
                "Eram 18 horas e 10 minutos."
            ),
        ),
    ]
    return ExtractedDocument(
        document_id="DAR-I-TEST",
        pages=pages,
        full_markdown="\n\n".join(page.markdown for page in pages),
    )


def test_detect_sections_splits_transcript_semantically() -> None:
    sections = detect_sections(_sample_extraction(), max_section_chars=1_000)

    assert [section.section_type for section in sections] == [
        "session_summary",
        "political_declaration",
        "vote",
    ]
    assert sections[0].section_id == "00-session-summary"
    assert sections[1].section_id == "01-declaracao-politica-do-pcp"
    assert sections[2].start_page == 3


def test_detect_sections_splits_oversized_sections_into_parts() -> None:
    extraction = _sample_extraction()
    long_text = "## DECLARAÇÃO POLÍTICA DO PSD\n" + ("Texto longo. " * 400)
    extraction.pages.append(
        ExtractedPage(
            document_id="DAR-I-TEST",
            page_number=4,
            markdown=long_text,
        )
    )

    sections = detect_sections(extraction, max_section_chars=800)
    ids = [section.section_id for section in sections]

    assert "03-declaracao-politica-do-psd-part-a" in ids
    assert "03-declaracao-politica-do-psd-part-b" in ids


def test_detect_sections_merges_page_furniture_and_consecutive_real_sections() -> None:
    extraction = ExtractedDocument(
        document_id="DAR-I-TEST",
        pages=[
            ExtractedPage(
                document_id="DAR-I-TEST",
                page_number=1,
                markdown="**I Série — Número 87**\nEm declaração política, a Deputada Paula Santos (PCP) pronunciou-se sobre o 1.º de Maio.",
            ),
            ExtractedPage(
                document_id="DAR-I-TEST",
                page_number=2,
                markdown="**7 DE MAIO DE 2026**\nEm declaração política, o Deputado Paulo Núncio (CDS-PP) defendeu a reforma laboral.",
            ),
        ],
        full_markdown="",
    )

    sections = detect_sections(extraction, max_section_chars=2_000)

    assert len(sections) == 1
    assert sections[0].section_type == "session_summary"
    assert sections[0].start_page == 1
    assert sections[0].end_page == 2


def test_detect_sections_merges_adjacent_speech_pages() -> None:
    extraction = ExtractedDocument(
        document_id="DAR-I-TEST",
        pages=[
            ExtractedPage(
                document_id="DAR-I-TEST",
                page_number=8,
                markdown="A Sr.ª **Paula Santos** (PCP): — Afirmaram bem alto a rejeição do pacote laboral.",
            ),
            ExtractedPage(
                document_id="DAR-I-TEST",
                page_number=9,
                markdown="A Sr.ª **Paula Santos** (PCP): — Não há remendo possível para uma proposta que mantém tudo o que é negativo.",
            ),
        ],
        full_markdown="",
    )

    sections = detect_sections(extraction, max_section_chars=5000)

    assert len(sections) == 1
    assert sections[0].start_page == 8
    assert sections[0].end_page == 9


def test_detect_sections_treats_continuation_page_as_same_section() -> None:
    extraction = ExtractedDocument(
        document_id="DAR-I-TEST",
        pages=[
            ExtractedPage(
                document_id="DAR-I-TEST",
                page_number=3,
                markdown=(
                    "SESSÃO SOLENE\n"
                    "O Sr. Presidente da Verkhovna Rada da Ucrânia (Ruslan Stefanchuk): — "
                    "Agradeço a solidariedade do Parlamento Português."
                ),
            ),
            ExtractedPage(
                document_id="DAR-I-TEST",
                page_number=4,
                markdown=(
                    "Representantes da comunidade ucraniana, membros do Governo e Sr.as e Srs. Deputados, "
                    "esta guerra mudou a Europa.\n"
                    "Esta noite, a Rússia violou o cessar-fogo e precisamos de apoio continuado."
                ),
            ),
        ],
        full_markdown="",
    )

    sections = detect_sections(extraction, max_section_chars=5_000)

    assert len(sections) == 1
    assert sections[0].section_type == "solemn_session"
    assert sections[0].start_page == 3
    assert sections[0].end_page == 4


def test_detect_sections_splits_mid_page_declaration_handoff() -> None:
    extraction = ExtractedDocument(
        document_id="DAR-I-TEST",
        pages=[
            ExtractedPage(
                document_id="DAR-I-TEST",
                page_number=17,
                markdown=(
                    "O Sr. Deputado Pedro Pinto (CH): — Respondo às questões colocadas.\n"
                    "Aplausos do CH.\n"
                    "O Sr. Presidente: — Tem agora a palavra, para uma declaração política, "
                    "o Sr. Deputado Paulo Núncio.\n"
                    "O Sr. Deputado Paulo Núncio (CDS-PP): — O mercado de trabalho precisa de reforma."
                ),
            ),
        ],
        full_markdown="",
    )

    sections = detect_sections(extraction, max_section_chars=5_000)

    assert len(sections) == 2
    assert sections[0].section_type == "speech"
    assert sections[0].start_page == 17
    assert sections[0].end_page == 17
    assert sections[1].section_type == "political_declaration"
    assert sections[1].start_page == 17
    assert sections[1].end_page == 17


def test_detect_sections_bounds_generated_section_id_length() -> None:
    extraction = ExtractedDocument(
        document_id="DAR-I-TEST",
        pages=[
            ExtractedPage(
                document_id="DAR-I-TEST",
                page_number=13,
                markdown=(
                    "E porque, junto dos melhores, junto dos maiores países da União Europeia, "
                    "tendo em consideração que Portugal atualmente tem 28 % a menos de produtividade "
                    "e 35 % a menos no salário bruto dos trabalhadores."
                ),
            ),
        ],
        full_markdown="",
    )

    sections = detect_sections(extraction, max_section_chars=5_000)

    assert len(sections) == 1
    assert sections[0].section_id.startswith("00-")
    assert len(sections[0].section_id) <= 120


def test_detect_sections_splits_mid_page_speaker_handoff() -> None:
    extraction = ExtractedDocument(
        document_id="DAR-I-TEST",
        pages=[
            ExtractedPage(
                document_id="DAR-I-TEST",
                page_number=19,
                markdown=(
                    "O Sr. **Pedro Pinto** (CH): — Vocês não gostam de elogiar.\n"
                    "O Sr. **Presidente** (Diogo Pacheco de Amorim): — Para o primeiro pedido de esclarecimento, "
                    "tem a palavra a Sr.ª Deputada Isaura Morais, do PSD.\n"
                    "A Sr.ª **Isaura Morais** (PSD): — Começo por saudar o tema que traz hoje na sua declaração política."
                ),
            ),
        ],
        full_markdown="",
    )

    sections = detect_sections(extraction, max_section_chars=5_000)

    assert len(sections) == 2
    assert sections[0].section_type == "speech"
    assert sections[1].section_type == "speech"
    assert "isaura morais" in sections[1].title


def test_detect_sections_skips_fragments_empty_after_furniture_stripping() -> None:
    extraction = ExtractedDocument(
        document_id="DAR-I-TEST",
        pages=[
            ExtractedPage(
                document_id="DAR-I-TEST",
                page_number=4,
                markdown="**I SÉRIE — NÚMERO 87**\n**4**",
            ),
            ExtractedPage(
                document_id="DAR-I-TEST",
                page_number=5,
                markdown="O Sr. **Presidente** : — Srs. Deputados, está aberta a sessão.",
            ),
        ],
        full_markdown="",
    )

    sections = detect_sections(extraction, max_section_chars=5_000)

    assert len(sections) == 1
    assert sections[0].start_page == 5
