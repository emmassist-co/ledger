from __future__ import annotations

from ledger.llm.types import GenerationResult
from ledger.models.artifacts import ArtifactLink, GenerationSummary, ViewArtifact


def write_index(
    document_id: str,
    notes,
    claims,
    references,
    generator,
) -> ViewArtifact:
    prompt = "\n\n".join(
        [
            "Write a Markdown document index in Portuguese for this parliamentary transcript.",
            "Use only the supplied episode notes, claims, and references.",
            "Do not introduce new facts.",
            "If a point is only a claim, keep it framed as a claim.",
            f"Document: {document_id}",
            "Episodes:",
            *[
                f"{note.episode_id} | {note.title}\nWhat happened: {note.what_happened}\nWhy it mattered: {note.why_it_mattered}\nClaims: {note.important_claims}"
                for note in notes
            ],
            "",
            "# Claims",
            *[f"{claim.claim_id}: {claim.claim}" for claim in claims],
            "",
            "# References",
            *[f"{reference.reference_id}: {reference.name}" for reference in references],
        ]
    )
    result = _generate_result(generator, prompt)
    return ViewArtifact(
        document_id=document_id,
        view_id="index",
        level=0,
        title="Índice do Documento",
        markdown=result.text,
        source_episodes=[
            ArtifactLink(id=note.episode_id, type="episode", path=f"./episodes/{note.episode_id}.md")
            for note in notes
        ],
        linked_claims=[
            ArtifactLink(id=claim.claim_id, type="claim", path=f"./claims/{claim.claim_id}.md")
            for claim in claims
        ],
        linked_references=[
            ArtifactLink(
                id=reference.reference_id,
                type="reference",
                path=f"./references/{reference.reference_id}.md",
            )
            for reference in references
        ],
        generation=GenerationSummary(
            event_id="",
            model=result.model,
            prompt_template="document-index@v1",
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            estimated_cost_usd=result.estimated_cost_usd,
        ),
    )


def _generate_result(generator, prompt: str) -> GenerationResult:
    if hasattr(generator, "generate_result"):
        return generator.generate_result(prompt)
    text = generator.generate(prompt)
    return GenerationResult(text=text, model="static")
