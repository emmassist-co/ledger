from __future__ import annotations

from ledger.models.artifacts import ArtifactLink, GenerationSummary, ViewArtifact


VIEW_CONFIG = {
    "level-1-simple": {"level": 1, "title": "O que aconteceu no Parlamento", "target_words": "200-400"},
    "level-2-standard": {"level": 2, "title": "Resumo político padrão", "target_words": "800-1300"},
    "level-3-detailed": {"level": 3, "title": "Leitura detalhada", "target_words": "2000-3500"},
}


def render_views(
    *,
    document_id: str,
    notes,
    claims,
    references,
    generators: dict[str, object],
) -> dict[str, ViewArtifact]:
    notes_block = "\n\n".join(
        f"## {note.title}\n{note.what_happened}\n{note.why_it_mattered}\nClaims: {note.important_claims}".strip()
        for note in notes
    )
    claim_block = "\n".join(f"- {claim.claim_id}: {claim.claim}" for claim in claims)
    ref_block = "\n".join(f"- {reference.reference_id}: {reference.name}" for reference in references)
    results: dict[str, ViewArtifact] = {}
    for view_name, generator in generators.items():
        config = VIEW_CONFIG[view_name]
        prompt = "\n\n".join(
            [
                "Generate a Portuguese Markdown explanation of this parliamentary transcript.",
                "Use only the provided episode notes, claims, and references.",
                "Do not introduce new facts.",
                "Keep claims labeled as claims.",
                f"Target length: {config['target_words']} words.",
                f"Document: {document_id}",
                f"View: {view_name}",
                notes_block,
                "# Claims",
                claim_block,
                "# References",
                ref_block,
            ]
        )
        result = _generate_result(generator, prompt)
        results[view_name] = ViewArtifact(
            document_id=document_id,
            view_id=view_name,
            level=config["level"],
            title=config["title"],
            markdown=result.text,
            source_episodes=[
                ArtifactLink(
                    id=note.episode_id,
                    type="episode",
                    path=f"../episodes/{note.episode_id}.md",
                )
                for note in notes
            ],
            linked_claims=[
                ArtifactLink(id=claim.claim_id, type="claim", path=f"../claims/{claim.claim_id}.md")
                for claim in claims
            ],
            linked_references=[
                ArtifactLink(
                    id=reference.reference_id,
                    type="reference",
                    path=f"../references/{reference.reference_id}.md",
                )
                for reference in references
            ],
            generation=GenerationSummary(
                event_id="",
                model=result.model,
                prompt_template=f"{view_name}@v1",
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                estimated_cost_usd=result.estimated_cost_usd,
            ),
        )
    return results


def _generate_result(generator, prompt: str):
    if hasattr(generator, "generate_result"):
        return generator.generate_result(prompt)
    text = generator.generate(prompt)
    return type("Result", (), {"text": text, "model": "static", "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0})()
