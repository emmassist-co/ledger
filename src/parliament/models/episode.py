from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Episode:
    document_id: str
    episode_id: str
    title: str
    episode_type: str
    start_page: int
    end_page: int
    text: str
    source_pages: list[int] = field(default_factory=list)
    segment_ids: list[str] = field(default_factory=list)
