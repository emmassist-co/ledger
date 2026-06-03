from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ledger.archive_index.paths import display_archive_path
from ledger.archive_index.web_index import WebIndexResult, index_markdown_webpage


DEFAULT_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class SourceCaptureResult:
    source_id: str
    source_url: str
    provider: str
    provider_detail: str | None
    local_path: Path
    manifest_path: Path
    sha256_hex: str
    markdown_tokens: int | None
    fetched_at: str
    web_index_result: WebIndexResult | None = None


class SourceCaptureError(RuntimeError):
    pass


@dataclass(frozen=True)
class CapturedMarkdownPayload:
    markdown: str
    provider: str
    provider_detail: str | None
    markdown_tokens: int | None


def fetch_public_webpage(
    *,
    root: Path,
    source_id: str,
    source_url: str,
    source_system: str | None = None,
    source_parent_url: str | None = None,
    download_path: Path | None = None,
    markdown_new_method: str = "auto",
    retain_images: bool = False,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> SourceCaptureResult:
    _validate_public_http_url(source_url)
    provider_attempts = [
        lambda: _fetch_via_markdown_new(
            source_url=source_url,
            method=markdown_new_method,
            retain_images=retain_images,
            timeout_seconds=timeout_seconds,
        ),
        lambda: _fetch_via_jina_reader(
            source_url=source_url,
            timeout_seconds=timeout_seconds,
        ),
    ]

    last_error: Exception | None = None
    payload: CapturedMarkdownPayload | None = None
    for attempt in provider_attempts:
        try:
            payload = attempt()
            break
        except SourceCaptureError as exc:
            last_error = exc
    if payload is None:
        detail = f": {last_error}" if last_error else ""
        raise SourceCaptureError(
            f"Failed to capture {source_url}{detail}. Try an agent browser only if the page truly requires rendering or interaction."
        )

    relative_download_path = download_path or Path("source") / "downloads" / f"{source_id}.md"
    if relative_download_path.is_absolute():
        raise SourceCaptureError("download_path must be relative to the archive root")
    local_path = root / relative_download_path
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(payload.markdown, encoding="utf-8")

    digest = sha256(payload.markdown.encode("utf-8")).hexdigest()
    manifest_path = root / "source" / "manifests" / "downloads.jsonl"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    fetched_at = _utc_now_isoformat()
    manifest_row = {
        "kind": "source_capture",
        "source_id": source_id,
        "source_system": source_system or _source_system_from_url(source_url),
        "source_url": source_url,
        "source_parent_url": source_parent_url,
        "local_path": display_archive_path(root, relative_download_path),
        "sha256": f"sha256:{digest}",
        "content_format": "markdown",
        "origin_format": "html",
        "capture_provider": payload.provider,
        "capture_provider_detail": payload.provider_detail,
        "capture_tokens": payload.markdown_tokens,
        "fetched_at": fetched_at,
    }
    _append_jsonl(manifest_path, manifest_row)

    web_index_result = index_markdown_webpage(
        root=root,
        source_id=source_id,
        markdown_path=relative_download_path,
        source_url=source_url,
    )

    return SourceCaptureResult(
        source_id=source_id,
        source_url=source_url,
        provider=payload.provider,
        provider_detail=payload.provider_detail,
        local_path=local_path,
        manifest_path=manifest_path,
        sha256_hex=digest,
        markdown_tokens=payload.markdown_tokens,
        fetched_at=fetched_at,
        web_index_result=web_index_result,
    )


def _fetch_via_markdown_new(
    *,
    source_url: str,
    method: str,
    retain_images: bool,
    timeout_seconds: int,
) -> CapturedMarkdownPayload:
    request = Request(
        "https://markdown.new/",
        data=json.dumps(
            {
                "url": source_url,
                "method": method,
                "retain_images": retain_images,
            }
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/markdown;q=0.9, text/plain;q=0.8",
            "User-Agent": "ledger/0.1",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body_text = response.read().decode("utf-8", errors="replace")
            content_type = response.headers.get("content-type", "")
            token_header = _parse_int_header(response.headers.get("x-markdown-tokens"))
    except (HTTPError, URLError) as exc:
        raise SourceCaptureError(f"markdown.new request failed: {exc}") from exc

    if "application/json" in content_type:
        try:
            data = json.loads(body_text)
        except json.JSONDecodeError as exc:
            raise SourceCaptureError("markdown.new returned invalid JSON") from exc
        markdown = str(data.get("content") or "").strip()
        if not markdown:
            raise SourceCaptureError("markdown.new returned empty markdown content")
        return CapturedMarkdownPayload(
            markdown=markdown + ("\n" if not markdown.endswith("\n") else ""),
            provider="markdown.new",
            provider_detail=str(data.get("method") or method or "auto"),
            markdown_tokens=_coalesce_int(token_header, data.get("tokens")),
        )

    markdown = body_text.strip()
    if not markdown:
        raise SourceCaptureError("markdown.new returned empty markdown body")
    return CapturedMarkdownPayload(
        markdown=markdown + ("\n" if not markdown.endswith("\n") else ""),
        provider="markdown.new",
        provider_detail=method,
        markdown_tokens=token_header,
    )


def _fetch_via_jina_reader(
    *,
    source_url: str,
    timeout_seconds: int,
) -> CapturedMarkdownPayload:
    request = Request(
        f"https://r.jina.ai/{source_url}",
        headers={
            "Accept": "text/plain",
            "User-Agent": "ledger/0.1",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body_text = response.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError) as exc:
        raise SourceCaptureError(f"Jina Reader request failed: {exc}") from exc

    markdown = _extract_jina_markdown(body_text)
    if not markdown.strip():
        raise SourceCaptureError("Jina Reader returned empty markdown content")
    return CapturedMarkdownPayload(
        markdown=markdown if markdown.endswith("\n") else markdown + "\n",
        provider="r.jina.ai",
        provider_detail="Reader API",
        markdown_tokens=None,
    )


def _extract_jina_markdown(body_text: str) -> str:
    marker = "Markdown Content:"
    if marker not in body_text:
        return body_text.strip()
    _, _, tail = body_text.partition(marker)
    markdown = tail.strip()
    if not markdown:
        return body_text.strip()

    title = _extract_prefixed_value(body_text, "Title:")
    if title and not markdown.startswith("# "):
        markdown = f"# {title}\n\n{markdown}"
    return markdown.strip()


def _extract_prefixed_value(text: str, prefix: str) -> str | None:
    for line in text.splitlines():
        if line.startswith(prefix):
            value = line.removeprefix(prefix).strip()
            return value or None
    return None


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({key: value for key, value in row.items() if value is not None}, ensure_ascii=False))
        handle.write("\n")
def _source_system_from_url(source_url: str) -> str:
    return urlparse(source_url).netloc


def _validate_public_http_url(source_url: str) -> None:
    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SourceCaptureError(f"Expected a public http(s) URL, got: {source_url}")


def _parse_int_header(raw_value: str | None) -> int | None:
    if raw_value is None:
        return None
    try:
        return int(raw_value)
    except ValueError:
        return None


def _coalesce_int(primary: int | None, secondary: object) -> int | None:
    if primary is not None:
        return primary
    if isinstance(secondary, int):
        return secondary
    return None


def _utc_now_isoformat() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
