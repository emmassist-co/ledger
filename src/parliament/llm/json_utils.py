from __future__ import annotations

import json
import re


def extract_json_object(text: str) -> dict[str, object]:
    stripped = text.strip()
    fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, re.DOTALL)
    if fenced_match:
        stripped = fenced_match.group(1)
    return json.loads(stripped)
