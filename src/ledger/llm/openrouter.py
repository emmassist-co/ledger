from __future__ import annotations

import json
from typing import Callable
from urllib import request

from ledger.llm.types import GenerationResult


Transport = Callable[[str, dict[str, str], dict[str, object]], dict[str, object]]

MODEL_PRICING_USD_PER_MILLION = {
    "openai/gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "deepseek/deepseek-v4-flash": {"input": 0.112, "output": 0.224},
    "deepseek/deepseek-chat-v3.1": {"input": 0.21, "output": 0.79},
}


class OpenRouterClient:
    endpoint = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: str, model: str, transport: Transport | None = None) -> None:
        self.api_key = api_key
        self.model = model
        self.transport = transport or _default_transport

    def build_payload(self, prompt: str) -> dict[str, object]:
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }

    def generate(self, prompt: str) -> str:
        return self.generate_result(prompt).text

    def generate_result(self, prompt: str) -> GenerationResult:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = self.build_payload(prompt)
        response = self.transport(self.endpoint, headers, payload)
        text = response["choices"][0]["message"]["content"]
        usage = response.get("usage", {})
        input_tokens = int(usage.get("prompt_tokens", 0))
        output_tokens = int(usage.get("completion_tokens", 0))
        pricing = MODEL_PRICING_USD_PER_MILLION.get(self.model, {"input": 0.0, "output": 0.0})
        estimated_cost_usd = (
            (input_tokens / 1_000_000) * pricing["input"]
            + (output_tokens / 1_000_000) * pricing["output"]
        )
        return GenerationResult(
            text=text,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost_usd,
        )


def _default_transport(
    url: str,
    headers: dict[str, str],
    payload: dict[str, object],
) -> dict[str, object]:
    body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(url, data=body, headers=headers, method="POST")
    with request.urlopen(http_request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))
