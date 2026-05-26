from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Sequence

from parliament.config import load_config, load_dotenv_file
from parliament.archive_index.dr_build import build_dr_outer_map, write_dr_outer_map
from parliament.archive_index.navigation import rebuild_navigation_index
from parliament.archive_index.paths import ArchiveIndexPaths
from parliament.dr.client import DrClient
from parliament.dr.discovery import discover_acts_from_search_hits
from parliament.dr.tax_vertical import build_tax_vertical
from parliament.explorer import write_explorer_html
from parliament.extract.page_map import build_page_map
from parliament.io.paths import DocumentPaths
from parliament.io.readers import read_episode_note
from parliament.io.writers import (
    append_generation_event,
    write_claim_artifact,
    write_episode_note,
    write_json_file,
    write_metadata,
    write_reference_artifact,
    write_text_file,
    write_view_artifact,
)
from parliament.llm.openrouter import OpenRouterClient
from parliament.llm.types import GenerationResult
from parliament.models.artifacts import (
    ArtifactLink,
    ClaimArtifact,
    EpisodeNote,
    GenerationEvent,
    GenerationSummary,
    ReferenceArtifact,
    ViewArtifact,
)
from parliament.pipeline.stages.detect_episodes import detect_episodes
from parliament.pipeline.stages.extract_claims_and_references import extract_claims_and_references
from parliament.pipeline.stages.parse_pdf import parse_pdf
from parliament.pipeline.stages.render_views import render_views
from parliament.pipeline.stages.write_episode_notes import write_episode_notes
from parliament.pipeline.stages.write_index import write_index


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="parliament")
    subparsers = parser.add_subparsers(dest="command", required=True)

    process_parser = subparsers.add_parser("process", help="Process one transcript PDF")
    process_parser.add_argument("pdf_path")
    process_parser.add_argument("--config", dest="config_path", type=Path)
    process_parser.add_argument("--document-id", dest="document_id")
    process_parser.add_argument("--output-root", dest="output_root", type=Path)
    process_parser.add_argument("--resume", action="store_true")
    process_parser.add_argument("--start-section", dest="start_section", type=int, default=0)
    process_parser.add_argument("--max-sections", dest="max_sections", type=int)

    explorer_parser = subparsers.add_parser("explorer", help="Generate a local HTML explorer for one processed document")
    explorer_parser.add_argument("document_root")

    archive_parser = subparsers.add_parser("archive", help="Operate on the archive index")
    archive_subparsers = archive_parser.add_subparsers(dest="archive_command", required=True)
    rebuild_parser = archive_subparsers.add_parser("rebuild-index", help="Rebuild the shared archive navigation index")
    rebuild_parser.add_argument("--root", type=Path, required=True)
    build_outer_map_parser = archive_subparsers.add_parser(
        "build-dr-outer-map", help="Build recent DR registry and facet coverage"
    )
    build_outer_map_parser.add_argument("--root", type=Path, required=True)
    build_outer_map_parser.add_argument("--window", default="recent")
    build_outer_map_parser.add_argument("--max-acts", type=int, default=50)
    build_tax_vertical_parser = archive_subparsers.add_parser(
        "build-dr-tax-vertical", help="Build the first deep DR tax vertical"
    )
    build_tax_vertical_parser.add_argument("--root", type=Path, required=True)
    build_tax_vertical_parser.add_argument("--anchor", default="irc")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "explorer":
        write_explorer_html(Path(args.document_root))
        return 0
    if args.command == "archive":
        if args.archive_command == "rebuild-index":
            rebuild_navigation_index(ArchiveIndexPaths(args.root))
            return 0
        if args.archive_command == "build-dr-outer-map":
            client = DrClient()
            hits = client.search_recent_legislation(max_acts=args.max_acts)
            discovered = discover_acts_from_search_hits(
                hits=hits,
                base_url="https://diariodarepublica.pt",
            )
            write_dr_outer_map(
                paths=ArchiveIndexPaths(args.root),
                discovered=discovered,
                source_parent_url="https://diariodarepublica.pt/dr/legislacao-por-data",
            )
            return 0
        if args.archive_command == "build-dr-tax-vertical":
            if args.anchor != "irc":
                parser.error(f"Unsupported DR tax anchor: {args.anchor}")
                return 2
            client = DrClient()
            act_source_url = "https://diariodarepublica.pt/dr/detalhe/decreto-lei/442-b-1988-519003"
            consolidated_url = "https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2014-64205634"
            act_detail = client.fetch_legislation_detail(
                source_url=act_source_url,
                content_id="519003",
                number_slug="442-b",
                year=1988,
                tipo="decreto-lei",
            )
            consolidated_document = client.fetch_consolidated_document(
                source_url=consolidated_url,
                diploma_frag_id="64205634",
                year=2014,
                tipo="lei",
            )
            build_tax_vertical(
                paths=ArchiveIndexPaths(args.root),
                anchor_id=args.anchor,
                act_detail=act_detail,
                consolidated_document=consolidated_document,
            )
            return 0
        parser.error(f"Unsupported archive command: {args.archive_command}")
        return 2
    if args.command != "process":
        parser.error(f"Unsupported command: {args.command}")
        return 2

    load_dotenv_file(Path(".env"))
    config = load_config(args.config_path)
    pdf_path = Path(args.pdf_path)
    document_id = args.document_id or pdf_path.stem
    output_root = args.output_root or Path(config.pipeline.output_root)
    paths = DocumentPaths.from_root(output_root, document_id)
    if not args.resume and args.start_section == 0:
        _reset_generated_outputs(paths)

    episode_generator = _build_generator(
        model=config.models.section_note,
        fake_output=os.getenv("PARLIAMENT_FAKE_LLM_OUTPUT"),
        stage="episode_note",
    )
    claims_generator = _build_generator(
        model=config.models.claims,
        fake_output=os.getenv("PARLIAMENT_FAKE_LLM_OUTPUT"),
        stage="claims",
    )
    index_generator = _build_generator(
        model=config.models.index,
        fake_output=os.getenv("PARLIAMENT_FAKE_LLM_OUTPUT"),
        stage="index",
    )
    view_generators = {
        "level-1-simple": _build_generator(
            model=config.models.level_1,
            fake_output=os.getenv("PARLIAMENT_FAKE_LLM_OUTPUT"),
            stage="view",
        ),
        "level-2-standard": _build_generator(
            model=config.models.level_2,
            fake_output=os.getenv("PARLIAMENT_FAKE_LLM_OUTPUT"),
            stage="view",
        ),
        "level-3-detailed": _build_generator(
            model=config.models.level_3,
            fake_output=os.getenv("PARLIAMENT_FAKE_LLM_OUTPUT"),
            stage="view",
        ),
    }

    extraction = parse_pdf(pdf_path, document_id)
    episodes = detect_episodes(extraction, max_section_chars=config.pipeline.max_section_chars)
    _write_source_outputs(paths, pdf_path, extraction)

    episode_order = {episode.episode_id: index for index, episode in enumerate(episodes)}
    existing_episode_ids = _load_existing_episode_ids(paths) if args.resume else set()
    target_episodes = _select_target_episodes(
        episodes,
        start_episode=args.start_section,
        max_episodes=args.max_sections,
        existing_episode_ids=existing_episode_ids,
    )
    for episode in target_episodes:
        note = write_episode_notes([episode], episode_generator)[0]
        event = _build_event(document_id, "episode", note.episode_id, note.generation, prompt_template="episode-note@v1")
        note = _with_generation(note, event)
        write_episode_note(paths, note)
        append_generation_event(paths, event)

    notes = _load_notes_for_episodes(paths, episodes)
    completed_episode_count = len(notes)
    episode_count = len(episodes)
    if completed_episode_count < episode_count:
        _write_partial_metadata(paths, extraction.document_id, len(extraction.pages), episode_count, completed_episode_count)
        return 0

    ordered_notes = sorted(notes, key=lambda note: episode_order.get(note.episode_id, 10**9))
    claims, references = extract_claims_and_references(document_id, ordered_notes, claims_generator)
    claims_batch_event = _build_shared_generation_event(
        document_id=document_id,
        artifact_type="claims_and_references",
        artifact_id="bundle",
        prompt_template="claims-and-references@v1",
        generations=[claim.generation for claim in claims] + [reference.generation for reference in references],
    )
    claims = [_with_claim_generation(claim, claims_batch_event) for claim in claims]
    for claim in claims:
        write_claim_artifact(paths, claim)

    references = _link_references(references, claims)
    references = [
        _with_reference_generation(
            reference,
            claims_batch_event,
        )
        for reference in references
    ]
    for reference in references:
        write_reference_artifact(paths, reference)
    append_generation_event(paths, claims_batch_event)

    _write_claim_index(paths, document_id, claims)
    _write_reference_index(paths, document_id, references)

    views = render_views(
        document_id=document_id,
        notes=ordered_notes,
        claims=claims,
        references=references,
        generators=view_generators,
    )
    for view_name, view in views.items():
        event = _build_event(document_id, "view", view_name, view.generation, prompt_template=f"{view_name}@v1")
        enriched_view = _with_view_generation(view, event)
        write_view_artifact(paths, enriched_view)
        append_generation_event(paths, event)

    index_view = write_index(document_id, ordered_notes, claims, references, index_generator)
    index_event = _build_event(document_id, "index", "index", index_view.generation, "document-index@v1")
    index_view = _with_view_generation(index_view, index_event)
    write_text_file(paths.document_root / "index.md", _render_index_file(index_view))
    append_generation_event(paths, index_event)

    write_metadata(
        paths,
        {
            "document_id": extraction.document_id,
            "page_count": len(extraction.pages),
            "episode_count": episode_count,
            "completed_episode_count": completed_episode_count,
            "claim_count": len(claims),
            "reference_count": len(references),
            "run_status": "complete",
            "resolver_status": "not_run",
            "verifier_status": "not_run",
            "cost_summary": _rollup_costs(paths),
        },
    )
    return 0


class _StaticGenerator:
    def __init__(self, content: str, model: str, stage: str) -> None:
        self.content = content
        self.model = model
        self.stage = stage

    def generate(self, prompt: str) -> str:
        return self.generate_result(prompt).text

    def generate_result(self, prompt: str) -> GenerationResult:
        if self.stage == "episode_note":
            text = (
                "{"
                f"\"topics\": [], \"actors\": [], \"parties\": [], \"importance\": \"medium\", "
                f"\"external_refs\": [], \"what_happened\": {self.content!r}, "
                "\"why_it_mattered\": \"\", \"main_actors\": \"\", \"party_positions\": \"\", "
                "\"important_claims\": \"\", \"external_references_to_check\": \"\", "
                "\"evidence_pointers\": [\"Page 1: placeholder evidence.\"]"
                "}"
            ).replace("'", '"')
        elif self.stage == "claims":
            text = "{\"claims\": [], \"references\": []}"
        else:
            text = self.content
        return GenerationResult(text=text, model=self.model)


def _build_generator(*, model: str, fake_output: str | None, stage: str):
    if fake_output is not None:
        return _StaticGenerator(fake_output, model=model, stage=stage)
    api_key = os.getenv("PARLIAMENT_OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Set PARLIAMENT_OPENROUTER_API_KEY or OPENROUTER_API_KEY, or set PARLIAMENT_FAKE_LLM_OUTPUT for local testing."
        )
    return OpenRouterClient(api_key=api_key, model=model)


def _write_source_outputs(paths: DocumentPaths, pdf_path: Path, extraction) -> None:
    paths.source_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pdf_path, paths.source_dir / pdf_path.name)
    write_text_file(paths.source_dir / "extracted_text.md", extraction.full_markdown)
    write_json_file(paths.source_dir / "page_map.json", build_page_map(extraction.pages))


def _load_existing_episode_ids(paths: DocumentPaths) -> set[str]:
    if not paths.episodes_dir.exists():
        return set()
    return {path.stem for path in paths.episodes_dir.glob("*.md")}


def _select_target_episodes(episodes, *, start_episode: int, max_episodes: int | None, existing_episode_ids: set[str]):
    if start_episode < 0:
        raise ValueError("--start-section must be non-negative")
    sliced = episodes[start_episode:]
    if max_episodes is not None:
        sliced = sliced[:max_episodes]
    return [episode for episode in sliced if episode.episode_id not in existing_episode_ids]


def _load_notes_for_episodes(paths: DocumentPaths, episodes) -> list[EpisodeNote]:
    notes: list[EpisodeNote] = []
    for episode in episodes:
        note_path = paths.episodes_dir / f"{episode.episode_id}.md"
        if note_path.exists():
            notes.append(read_episode_note(note_path))
    return notes


def _write_partial_metadata(paths: DocumentPaths, document_id: str, page_count: int, episode_count: int, completed_episode_count: int) -> None:
    write_metadata(
        paths,
        {
            "document_id": document_id,
            "page_count": page_count,
            "episode_count": episode_count,
            "completed_episode_count": completed_episode_count,
            "run_status": "partial",
            "resolver_status": "not_run",
            "verifier_status": "not_run",
        },
    )


def _write_claim_index(paths: DocumentPaths, document_id: str, claims: list[ClaimArtifact]) -> None:
    lines = [
        "---",
        f"document_id: {document_id}",
        "artifact_type: claim_index",
        "---",
        "",
        "# Claims Index",
        "",
    ]
    for claim in claims:
        lines.extend(
            [
                f"## [{claim.title}](./{claim.claim_id}.md)",
                "",
                f"- Speaker: {claim.speaker}",
                f"- Party: {claim.party}",
                f"- Episode: [{claim.episode.id}]({claim.episode.path})",
                f"- Verification status: {claim.verification_status}",
                "",
            ]
        )
    write_text_file(paths.claims_dir / "index.md", "\n".join(lines).strip() + "\n")


def _write_reference_index(paths: DocumentPaths, document_id: str, references: list[ReferenceArtifact]) -> None:
    lines = [
        "---",
        f"document_id: {document_id}",
        "artifact_type: reference_index",
        "---",
        "",
        "# References Index",
        "",
    ]
    for reference in references:
        lines.extend(
            [
                f"## [{reference.title}](./{reference.reference_id}.md)",
                "",
                f"- Priority: {reference.priority}",
                f"- Linked claims: {len(reference.linked_claims)}",
                "",
            ]
        )
    write_text_file(paths.references_dir / "index.md", "\n".join(lines).strip() + "\n")


def _render_index_file(view: ViewArtifact) -> str:
    frontmatter = {
        "document_id": view.document_id,
        "view_id": view.view_id,
        "artifact_type": "index",
        "title": view.title,
        "source_episodes": [link.to_dict() for link in view.source_episodes],
        "linked_claims": [link.to_dict() for link in view.linked_claims],
        "linked_references": [link.to_dict() for link in view.linked_references],
        "generation": view.generation.to_dict() if view.generation else None,
    }
    from parliament.render.frontmatter import render_frontmatter

    return render_frontmatter({key: value for key, value in frontmatter.items() if value is not None}) + "\n" + view.markdown.strip() + "\n"


def _reset_generated_outputs(paths: DocumentPaths) -> None:
    for directory in (paths.episodes_dir, paths.claims_dir, paths.references_dir, paths.views_dir, paths.runs_dir):
        if directory.exists():
            shutil.rmtree(directory)
    for file_path in (paths.document_root / "index.md", paths.document_root / "metadata.json"):
        if file_path.exists():
            file_path.unlink()


def _build_event(document_id: str, artifact_type: str, artifact_id: str, generation: GenerationSummary | None, prompt_template: str) -> GenerationEvent:
    generation = generation or GenerationSummary(
        event_id="",
        model="static",
        prompt_template=prompt_template,
        input_tokens=0,
        output_tokens=0,
        estimated_cost_usd=0.0,
    )
    event_id = f"gen-{artifact_type}-{artifact_id}"
    return GenerationEvent(
        event_id=event_id,
        document_id=document_id,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        model=generation.model,
        prompt_template=prompt_template,
        input_tokens=generation.input_tokens,
        output_tokens=generation.output_tokens,
        estimated_cost_usd=generation.estimated_cost_usd,
        status="success",
    )


def _build_shared_generation_event(
    *,
    document_id: str,
    artifact_type: str,
    artifact_id: str,
    prompt_template: str,
    generations: list[GenerationSummary | None],
) -> GenerationEvent:
    generation = next((item for item in generations if item is not None), None)
    return _build_event(document_id, artifact_type, artifact_id, generation, prompt_template)


def _with_generation(note: EpisodeNote, event: GenerationEvent) -> EpisodeNote:
    return EpisodeNote(**{**note.__dict__, "generation": GenerationSummary(
        event_id=event.event_id,
        model=event.model,
        prompt_template=event.prompt_template,
        input_tokens=event.input_tokens,
        output_tokens=event.output_tokens,
        estimated_cost_usd=event.estimated_cost_usd,
    )})


def _with_claim_generation(claim: ClaimArtifact, event: GenerationEvent) -> ClaimArtifact:
    return ClaimArtifact(**{**claim.__dict__, "generation": GenerationSummary(
        event_id=event.event_id,
        model=event.model,
        prompt_template=event.prompt_template,
        input_tokens=event.input_tokens,
        output_tokens=event.output_tokens,
        estimated_cost_usd=event.estimated_cost_usd,
    )})


def _with_reference_generation(reference: ReferenceArtifact, event: GenerationEvent) -> ReferenceArtifact:
    return ReferenceArtifact(**{**reference.__dict__, "generation": GenerationSummary(
        event_id=event.event_id,
        model=event.model,
        prompt_template=event.prompt_template,
        input_tokens=event.input_tokens,
        output_tokens=event.output_tokens,
        estimated_cost_usd=event.estimated_cost_usd,
    )})


def _with_view_generation(view: ViewArtifact, event: GenerationEvent) -> ViewArtifact:
    return ViewArtifact(**{**view.__dict__, "generation": GenerationSummary(
        event_id=event.event_id,
        model=event.model,
        prompt_template=event.prompt_template,
        input_tokens=event.input_tokens,
        output_tokens=event.output_tokens,
        estimated_cost_usd=event.estimated_cost_usd,
    )})


def _link_references(references: list[ReferenceArtifact], claims: list[ClaimArtifact]) -> list[ReferenceArtifact]:
    reference_map = {reference.reference_id: reference for reference in references}
    for claim in claims:
        for link in claim.references:
            reference = reference_map.get(link.id)
            if reference is None:
                continue
            if not any(existing.id == claim.claim_id for existing in reference.linked_claims):
                reference.linked_claims.append(
                    ArtifactLink(
                        id=claim.claim_id,
                        type="claim",
                        path=f"../claims/{claim.claim_id}.md",
                        relationship="supports_verification",
                    )
                )
            if claim.episode.id and not any(existing.id == claim.episode.id for existing in reference.linked_episodes):
                reference.linked_episodes.append(claim.episode)
    return references


def _rollup_costs(paths: DocumentPaths) -> dict[str, object]:
    events_path = paths.runs_dir / "events.jsonl"
    if not events_path.exists():
        return {"total_estimated_cost_usd": 0.0, "by_artifact_type": {}}
    by_type: dict[str, float] = {}
    total = 0.0
    for line in events_path.read_text().splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        cost = float(event.get("estimated_cost_usd", 0.0))
        total += cost
        by_type[event["artifact_type"]] = by_type.get(event["artifact_type"], 0.0) + cost
    return {"total_estimated_cost_usd": round(total, 8), "by_artifact_type": by_type}
