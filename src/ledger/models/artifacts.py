from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class ArtifactLink:
    id: str
    type: str
    path: str
    relationship: str | None = None
    anchor: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        return {key: value for key, value in payload.items() if value is not None}


@dataclass(frozen=True)
class GenerationSummary:
    event_id: str
    model: str
    prompt_template: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class EpisodeNote:
    document_id: str
    episode_id: str
    title: str
    episode_type: str
    pages: list[int]
    topics: list[str] = field(default_factory=list)
    actors: list[str] = field(default_factory=list)
    parties: list[str] = field(default_factory=list)
    importance: str = "medium"
    references: list[ArtifactLink] = field(default_factory=list)
    claims: list[ArtifactLink] = field(default_factory=list)
    generation: GenerationSummary | None = None
    what_happened: str = ""
    why_it_mattered: str = ""
    main_actors: str = ""
    party_positions: str = ""
    important_claims: str = ""
    external_references_to_check: str = ""
    evidence_pointers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ClaimArtifact:
    document_id: str
    claim_id: str
    title: str
    claim: str
    speaker: str
    party: str
    claim_type: str
    verification_status: str
    priority: str
    episode: ArtifactLink
    references: list[ArtifactLink] = field(default_factory=list)
    source_mention: str = ""
    generation: GenerationSummary | None = None


@dataclass(frozen=True)
class ReferenceArtifact:
    document_id: str
    reference_id: str
    title: str
    name: str
    priority: str
    description: str
    linked_claims: list[ArtifactLink] = field(default_factory=list)
    linked_episodes: list[ArtifactLink] = field(default_factory=list)
    generation: GenerationSummary | None = None


@dataclass(frozen=True)
class ViewArtifact:
    document_id: str
    view_id: str
    level: int
    title: str
    markdown: str
    source_episodes: list[ArtifactLink] = field(default_factory=list)
    linked_claims: list[ArtifactLink] = field(default_factory=list)
    linked_references: list[ArtifactLink] = field(default_factory=list)
    generation: GenerationSummary | None = None


@dataclass(frozen=True)
class GenerationEvent:
    event_id: str
    document_id: str
    artifact_type: str
    artifact_id: str
    model: str
    prompt_template: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    status: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
