from __future__ import annotations

from parliament.llm.json_utils import extract_json_object
from parliament.models.artifacts import ArtifactLink, ClaimArtifact, GenerationSummary, ReferenceArtifact
from parliament.sectioning.normalizer import slugify


def extract_claims_and_references(
    document_id: str,
    notes,
    generator,
) -> tuple[list[ClaimArtifact], list[ReferenceArtifact]]:
    prompt = "\n\n".join(
        [
            "Extract only claims worth checking from these episode notes.",
            "Return JSON only.",
            "Rules:",
            "- Include statistical, legal, historical, programmatic, report-backed, or otherwise disputable claims.",
            "- Keep speaker, party, episode_id, claim text, type, source mention, external references, priority.",
            "- Return normalized references separately.",
            f"Document: {document_id}",
            "Claims input:",
            *[
                f"Episode: {note.episode_id}\nTitle: {note.title}\nClaims: {note.important_claims}\nRefs: {note.external_references_to_check}\nActors: {', '.join(note.actors)}\nParties: {', '.join(note.parties)}"
                for note in notes
                if note.important_claims.strip()
            ],
            "",
            "Return JSON with keys `claims` and `references`.",
        ]
    )
    result = _generate_result(generator, prompt)
    generated = extract_json_object(result.text)

    claims: list[ClaimArtifact] = []
    references_by_name: dict[str, ReferenceArtifact] = {}

    episode_by_id = {note.episode_id: note for note in notes}
    for note in notes:
        for ref_name in _split_reference_text(note.external_references_to_check):
            reference = references_by_name.get(ref_name)
            if reference is None:
                reference = ReferenceArtifact(
                    document_id=document_id,
                    reference_id=_reference_id_for_name(ref_name),
                    title=ref_name,
                    name=ref_name,
                    priority="medium",
                    description=ref_name,
                    linked_claims=[],
                    linked_episodes=[],
                    generation=GenerationSummary(
                        event_id="",
                        model=result.model,
                        prompt_template="claims-and-references@v1",
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        estimated_cost_usd=result.estimated_cost_usd,
                    ),
                )
                references_by_name[ref_name] = reference
            reference.linked_episodes.append(
                ArtifactLink(
                    id=note.episode_id,
                    type="episode",
                    path=f"../episodes/{note.episode_id}.md",
                    relationship="mentioned_in_episode",
                )
            )

    for index, claim_obj in enumerate(generated.get("claims", []), start=1):
        claim_data = claim_obj if isinstance(claim_obj, dict) else {"claim": str(claim_obj)}
        claim_id = f"clm-{index:04d}-{slugify(str(claim_data.get('claim', 'claim')))[:50].strip('-') or 'claim'}"
        episode_id = str(claim_data.get("episode_id", notes[0].episode_id if notes else ""))
        episode_path = f"../episodes/{episode_id}.md" if episode_id else ""
        reference_names = _normalize_reference_names(claim_data.get("references") or claim_data.get("external_references") or claim_data.get("external_source_mentioned"))
        claim_references = []
        for ref_name in reference_names:
            reference = references_by_name.get(ref_name)
            if reference is None:
                ref_id = _reference_id_for_name(ref_name)
                reference = ReferenceArtifact(
                    document_id=document_id,
                    reference_id=ref_id,
                    title=ref_name,
                    name=ref_name,
                    priority=str(claim_data.get("priority", "medium")),
                    description=str(claim_data.get("source_mention") or ref_name),
                    linked_claims=[],
                    linked_episodes=[],
                    generation=GenerationSummary(
                        event_id="",
                        model=result.model,
                        prompt_template="claims-and-references@v1",
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        estimated_cost_usd=result.estimated_cost_usd,
                    ),
                )
                references_by_name[ref_name] = reference
            ref_id = reference.reference_id
            claim_references.append(
                ArtifactLink(
                    id=ref_id,
                    type="reference",
                    path=f"../references/{ref_id}.md",
                    relationship="needs_verification",
                )
            )
        claim = ClaimArtifact(
            document_id=document_id,
            claim_id=claim_id,
            title=str(claim_data.get("title") or claim_data.get("claim") or claim_id),
            claim=str(claim_data.get("claim", "")),
            speaker=str(claim_data.get("speaker", "")),
            party=str(claim_data.get("party", "")),
            claim_type=str(claim_data.get("type", "")),
            verification_status=str(claim_data.get("verification_status", "not_checked")),
            priority=str(claim_data.get("priority", "medium")),
            episode=ArtifactLink(
                id=episode_id,
                type="episode",
                path=episode_path,
                relationship="made_in_episode",
            ),
            references=claim_references,
            source_mention=str(claim_data.get("source_mention") or claim_data.get("external_source_mentioned") or ""),
            generation=GenerationSummary(
                event_id="",
                model=result.model,
                prompt_template="claims-and-references@v1",
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                estimated_cost_usd=result.estimated_cost_usd,
            ),
        )
        claims.append(claim)

    for claim in claims:
        for link in claim.references:
            reference = next(ref for ref in references_by_name.values() if ref.reference_id == link.id)
            reference.linked_claims.append(
                ArtifactLink(
                    id=claim.claim_id,
                    type="claim",
                    path=f"../claims/{claim.claim_id}.md",
                    relationship="supports_verification",
                )
            )
            if claim.episode.id:
                reference.linked_episodes.append(claim.episode)

    references = list(references_by_name.values())
    for ref_obj in generated.get("references", []):
        if not isinstance(ref_obj, dict):
            continue
        name = str(ref_obj.get("name", "")).strip()
        if not name or name in references_by_name:
            continue
        reference = ReferenceArtifact(
            document_id=document_id,
            reference_id=_reference_id_for_name(name),
            title=name,
            name=name,
            priority=str(ref_obj.get("priority", "medium")),
            description=str(ref_obj.get("reason", name)),
            generation=GenerationSummary(
                event_id="",
                model=result.model,
                prompt_template="claims-and-references@v1",
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                estimated_cost_usd=result.estimated_cost_usd,
            ),
        )
        references_by_name[name] = reference
        references.append(reference)

    return claims, references


def _normalize_reference_names(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return [str(value).strip()]


def _split_reference_text(value: str) -> list[str]:
    items: list[str] = []
    for chunk in value.split(";"):
        normalized = chunk.strip()
        if normalized:
            items.append(normalized)
    return items


def _reference_id_for_name(name: str) -> str:
    slug = slugify(name)[:50].strip("-") or "reference"
    return f"ref-{slug}"


def _generate_result(generator, prompt: str):
    if hasattr(generator, "generate_result"):
        return generator.generate_result(prompt)
    text = generator.generate(prompt)
    return type("Result", (), {"text": text, "model": "static", "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0})()
