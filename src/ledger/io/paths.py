from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DocumentPaths:
    document_root: Path
    source_dir: Path
    episodes_dir: Path
    claims_dir: Path
    references_dir: Path
    views_dir: Path
    runs_dir: Path

    @classmethod
    def from_root(cls, output_root: Path, document_id: str) -> "DocumentPaths":
        document_root = output_root / document_id
        return cls(
            document_root=document_root,
            source_dir=document_root / "source",
            episodes_dir=document_root / "episodes",
            claims_dir=document_root / "claims",
            references_dir=document_root / "references",
            views_dir=document_root / "views",
            runs_dir=document_root / "runs",
        )
