from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GenerationResult:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
