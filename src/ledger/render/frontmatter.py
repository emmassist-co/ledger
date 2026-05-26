from __future__ import annotations

import yaml

def render_frontmatter(data: dict[str, object]) -> str:
    body = yaml.safe_dump(data, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{body}\n---\n"
