from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Section:
    document_id: str
    section_id: str
    title: str
    section_type: str
    start_page: int
    end_page: int
    text: str
    source_pages: list[int] = field(default_factory=list)
