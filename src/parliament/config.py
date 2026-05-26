from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ModelConfig:
    section_note: str = "openrouter/openai/gpt-4.1-mini"
    claims: str = "openrouter/openai/gpt-4.1-mini"
    index: str = "openrouter/openai/gpt-4.1-mini"
    level_1: str = "openrouter/openai/gpt-4.1-mini"
    level_2: str = "openrouter/openai/gpt-4.1-mini"
    level_3: str = "openrouter/openai/gpt-4.1-mini"


@dataclass(frozen=True)
class PipelineConfig:
    output_root: str = "documents"
    max_section_chars: int = 12_000
    enable_resolver: bool = False


@dataclass(frozen=True)
class AppConfig:
    models: ModelConfig
    pipeline: PipelineConfig


def _merge_defaults(raw_data: dict[str, Any]) -> AppConfig:
    model_data = raw_data.get("models", {})
    pipeline_data = raw_data.get("pipeline", {})

    return AppConfig(
        models=ModelConfig(**model_data),
        pipeline=PipelineConfig(**pipeline_data),
    )


def load_config(config_path: Path | None) -> AppConfig:
    if config_path is None:
        return _merge_defaults({})

    raw_data = yaml.safe_load(config_path.read_text()) or {}
    return _merge_defaults(raw_data)


def load_dotenv_file(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)
