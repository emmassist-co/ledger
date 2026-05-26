from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ArchiveCorpusPaths:
    corpus_name: str
    artifacts_root: Path
    source_root: Path

    @property
    def registry_dir(self) -> Path:
        return self.artifacts_root / "registry"

    @property
    def acts_dir(self) -> Path:
        return self.artifacts_root / "acts"

    @property
    def article_blocks_dir(self) -> Path:
        return self.artifacts_root / "article-blocks"

    @property
    def consolidation_notes_dir(self) -> Path:
        return self.artifacts_root / "consolidation-notes"

    @property
    def relations_dir(self) -> Path:
        return self.artifacts_root / "relations"

    @property
    def facets_dir(self) -> Path:
        return self.artifacts_root / "facets"

    def artifact_path(self, artifact_type: str, artifact_id: str) -> Path:
        directory_map = {
            "registry": self.registry_dir,
            "act": self.acts_dir,
            "article_block": self.article_blocks_dir,
            "consolidation_note": self.consolidation_notes_dir,
            "relation": self.relations_dir,
            "facet": self.facets_dir,
        }
        try:
            directory = directory_map[artifact_type]
        except KeyError as exc:
            raise ValueError(f"Unsupported archive artifact type: {artifact_type}") from exc
        return directory / f"{artifact_id}.md"


@dataclass(frozen=True)
class ArchiveIndexPaths:
    root: Path

    @property
    def artifacts_root(self) -> Path:
        return self.root / "artifacts"

    @property
    def index_root(self) -> Path:
        return self.root / "index"

    @property
    def source_root(self) -> Path:
        return self.root / "source"

    def corpus(self, corpus_name: str) -> ArchiveCorpusPaths:
        return ArchiveCorpusPaths(
            corpus_name=corpus_name,
            artifacts_root=self.artifacts_root / corpus_name,
            source_root=self.source_root / corpus_name,
        )
