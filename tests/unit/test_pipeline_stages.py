from __future__ import annotations

from parliament.models.artifacts import EpisodeNote
from parliament.models.episode import Episode
from parliament.pipeline.stages.extract_claims_and_references import extract_claims_and_references
from parliament.pipeline.stages.render_views import render_views
from parliament.pipeline.stages.write_episode_notes import write_episode_notes
from parliament.pipeline.stages.write_index import write_index


class FakeGenerator:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "Generated text"


def test_write_episode_notes_uses_episode_text_and_generates_notes() -> None:
    generator = FakeGenerator()
    generator.generate = lambda prompt: """
{
  "topics": ["Ucrânia", "solidariedade europeia"],
  "actors": ["Ruslan Stefanchuk", "José Pedro Aguiar-Branco"],
  "parties": ["PCP"],
  "importance": "high",
  "external_refs": ["adesão da Ucrânia à UE"],
  "what_happened": "Sessão solene de boas-vindas ao Presidente da Verkhovna Rada da Ucrânia.",
  "why_it_mattered": "Reforçou o apoio institucional português à Ucrânia.",
  "main_actors": "Intervieram Ruslan Stefanchuk e o Presidente da Assembleia da República.",
  "party_positions": "Houve aplausos gerais e registo da ausência do PCP.",
  "important_claims": "Stefanchuk afirmou que a Rússia violou o cessar-fogo proposto por Zelenskyy.",
  "external_references_to_check": "cessar-fogo proposto por Zelenskyy; adesão da Ucrânia à UE",
  "evidence_pointers": ["Page 3: abertura da sessão solene."]
}
""".strip()
    episodes = [
        Episode(
            document_id="DAR-I-TEST",
            episode_id="ep-0001-test",
            title="Teste",
            episode_type="solemn_session",
            start_page=2,
            end_page=3,
            text="Texto do episódio",
            source_pages=[2, 3],
        )
    ]

    notes = write_episode_notes(episodes, generator)

    assert notes[0].episode_id == "ep-0001-test"
    assert notes[0].what_happened.startswith("Sessão solene")
    assert notes[0].topics == ["Ucrânia", "solidariedade europeia"]
    assert notes[0].importance == "high"


def test_extract_claims_and_references_returns_atomic_artifacts() -> None:
    generator = FakeGenerator()
    generator.generate = lambda prompt: """
{
  "claims": [
    {
      "speaker": "Paula Santos",
      "party": "PCP",
      "episode_id": "ep-0001-test",
      "claim": "10% detêm 60% da riqueza.",
      "type": "statistical",
      "external_source_mentioned": "Comissão Europeia",
      "priority": "high",
      "verification_status": "not_checked"
    }
  ],
  "references": [
    {
      "name": "Comissão Europeia",
      "priority": "high",
      "reason": "Fonte mencionada no episódio."
    }
  ]
}
""".strip()
    notes = [
        EpisodeNote(
            document_id="DAR-I-TEST",
            episode_id="ep-0001-test",
            title="Teste",
            episode_type="declaration_block",
            pages=[2, 3],
            important_claims="Paula Santos afirmou que 10% detêm 60% da riqueza.",
            external_references_to_check="Comissão Europeia",
        )
    ]

    claims, references = extract_claims_and_references("DAR-I-TEST", notes, generator)

    assert claims[0].speaker == "Paula Santos"
    assert claims[0].episode.id == "ep-0001-test"
    assert references[0].name == "Comissão Europeia"


def test_extract_claims_and_references_reuses_same_reference_id_across_claims() -> None:
    generator = FakeGenerator()
    generator.generate = lambda prompt: """
{
  "claims": [
    {
      "speaker": "Paula Santos",
      "party": "PCP",
      "episode_id": "ep-0001-test",
      "claim": "Primeira afirmação.",
      "type": "statistical",
      "external_source_mentioned": "Comissão Europeia",
      "priority": "high",
      "verification_status": "not_checked"
    },
    {
      "speaker": "Paulo Núncio",
      "party": "CDS-PP",
      "episode_id": "ep-0002-test",
      "claim": "Segunda afirmação.",
      "type": "policy_comparison",
      "external_source_mentioned": "Comissão Europeia",
      "priority": "medium",
      "verification_status": "not_checked"
    }
  ],
  "references": []
}
""".strip()
    notes = [
        EpisodeNote(
            document_id="DAR-I-TEST",
            episode_id="ep-0001-test",
            title="Teste 1",
            episode_type="declaration_block",
            pages=[2, 3],
            important_claims="Primeira afirmação.",
        ),
        EpisodeNote(
            document_id="DAR-I-TEST",
            episode_id="ep-0002-test",
            title="Teste 2",
            episode_type="declaration_block",
            pages=[4, 5],
            important_claims="Segunda afirmação.",
        ),
    ]

    claims, references = extract_claims_and_references("DAR-I-TEST", notes, generator)

    assert len(references) == 1
    assert claims[0].references[0].id == claims[1].references[0].id


def test_extract_claims_and_references_seeds_references_from_episode_notes() -> None:
    generator = FakeGenerator()
    generator.generate = lambda prompt: """
{
  "claims": [],
  "references": []
}
""".strip()
    notes = [
        EpisodeNote(
            document_id="DAR-I-TEST",
            episode_id="ep-0001-test",
            title="Teste 1",
            episode_type="declaration_block",
            pages=[2, 3],
            external_references_to_check="Comissão Europeia; OCDE labour-market rigidity ranking",
        )
    ]

    claims, references = extract_claims_and_references("DAR-I-TEST", notes, generator)

    assert claims == []
    assert [reference.name for reference in references] == [
        "Comissão Europeia",
        "OCDE labour-market rigidity ranking",
    ]
    assert references[0].linked_episodes[0].id == "ep-0001-test"


def test_render_views_and_index_use_episode_notes() -> None:
    generator = FakeGenerator()
    notes = [
        EpisodeNote(
            document_id="DAR-I-TEST",
            episode_id="ep-0001-test",
            title="Teste",
            episode_type="declaration_block",
            pages=[2, 3],
            what_happened="Nota resumida",
            important_claims="Sem números.",
        )
    ]
    claims, references = [], []

    views = render_views(
        document_id="DAR-I-TEST",
        notes=notes,
        claims=claims,
        references=references,
        generators={
            "level-1-simple": generator,
            "level-2-standard": generator,
            "level-3-detailed": generator,
        },
    )
    index_view = write_index("DAR-I-TEST", notes, claims, references, generator)

    assert views["level-1-simple"].markdown == "Generated text"
    assert "Nota resumida" in generator.prompts[0]
    assert index_view.markdown == "Generated text"
