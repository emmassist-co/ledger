from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClaimRecord:
    speaker: str
    party: str
    section_id: str
    claim: str
    claim_type: str
    external_source_mentioned: str | None
    priority: str
    verification_status: str = "not_checked"


@dataclass(frozen=True)
class ReferenceRecord:
    name: str
    priority: str
    reason: str
