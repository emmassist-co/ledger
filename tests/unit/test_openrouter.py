from __future__ import annotations

import json
from pathlib import Path

from ledger.llm.openrouter import OpenRouterClient
from ledger.llm.prompts import load_prompt_template


def test_load_prompt_template_reads_prompt_file(tmp_path: Path) -> None:
    prompt_path = tmp_path / "section-note.md"
    prompt_path.write_text("Prompt for {title}")

    loaded = load_prompt_template(prompt_path)

    assert loaded == "Prompt for {title}"


def test_openrouter_client_builds_expected_request_payload() -> None:
    client = OpenRouterClient(
        api_key="test-key",
        model="openrouter/test-model",
    )

    payload = client.build_payload("Summarize this")

    assert payload["model"] == "openrouter/test-model"
    assert payload["messages"][0]["content"] == "Summarize this"


def test_openrouter_client_returns_message_content_from_response() -> None:
    seen: dict[str, object] = {}

    def fake_transport(url: str, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
        seen["url"] = url
        seen["headers"] = headers
        seen["payload"] = payload
        return {
            "choices": [
                {
                    "message": {
                        "content": "markdown output",
                    }
                }
            ]
        }

    client = OpenRouterClient(
        api_key="test-key",
        model="openrouter/test-model",
        transport=fake_transport,
    )

    result = client.generate("Write note")

    assert result == "markdown output"
    assert seen["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert seen["headers"]["Authorization"] == "Bearer test-key"
    assert seen["payload"]["model"] == "openrouter/test-model"
