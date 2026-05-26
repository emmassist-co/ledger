from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ArchiveArtifact:
    path: Path
    metadata: dict[str, object]
    body: str


def write_archive_artifact(*, path: Path, frontmatter: dict[str, object], body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned_frontmatter = {key: value for key, value in frontmatter.items() if value is not None}
    path.write_text(_render_frontmatter(cleaned_frontmatter) + body)
    return path


def read_archive_artifact(path: Path) -> ArchiveArtifact:
    raw = path.read_text()
    frontmatter, body = _split_frontmatter(raw)
    metadata = yaml.safe_load(frontmatter) or {}
    return ArchiveArtifact(path=path, metadata=metadata, body=body)


def _split_frontmatter(raw: str) -> tuple[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.DOTALL)
    if not match:
        raise ValueError("Invalid markdown artifact frontmatter")
    return match.group(1), match.group(2)


def _render_frontmatter(data: dict[str, object]) -> str:
    body = yaml.safe_dump(data, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{body}\n---\n"
