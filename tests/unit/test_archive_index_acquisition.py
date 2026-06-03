from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from ledger.archive_index import acquisition


class FakeHeaders(dict):
    def get(self, key: str, default: str | None = None) -> str | None:
        return super().get(key.lower(), default)


class FakeResponse:
    def __init__(self, body: str, *, headers: dict[str, str] | None = None) -> None:
        self._body = body.encode("utf-8")
        self.headers = FakeHeaders({key.lower(): value for key, value in (headers or {}).items()})

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_fetch_public_webpage_uses_markdown_new_and_appends_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_urlopen(request, timeout: int = 0):
        assert request.full_url == "https://markdown.new/"
        payload = json.loads(request.data.decode("utf-8"))
        assert payload["url"] == "https://example.com/path"
        assert payload["method"] == "browser"
        return FakeResponse(
            json.dumps(
                {
                    "success": True,
                    "content": "# Example\n\nClean markdown.\n",
                    "method": "Cloudflare Browser Rendering",
                    "tokens": 17,
                }
            ),
            headers={
                "content-type": "application/json; charset=utf-8",
                "x-markdown-tokens": "17",
            },
        )

    monkeypatch.setattr(acquisition, "urlopen", fake_urlopen)

    result = acquisition.fetch_public_webpage(
        root=tmp_path / "archive-index",
        source_id="example-path",
        source_url="https://example.com/path",
        source_parent_url="https://example.com",
        markdown_new_method="browser",
    )

    assert result.provider == "markdown.new"
    assert result.provider_detail == "Cloudflare Browser Rendering"
    assert result.markdown_tokens == 17
    assert result.local_path.read_text(encoding="utf-8") == "# Example\n\nClean markdown.\n"
    assert result.web_index_result is not None
    assert result.web_index_result.section_count >= 1
    assert result.web_index_result.sqlite_path.exists()

    rows = result.manifest_path.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1
    manifest = json.loads(rows[0])
    assert manifest["kind"] == "source_capture"
    assert manifest["source_url"] == "https://example.com/path"
    assert manifest["source_parent_url"] == "https://example.com"
    assert manifest["content_format"] == "markdown"
    assert manifest["origin_format"] == "html"
    assert manifest["capture_provider"] == "markdown.new"
    assert manifest["capture_tokens"] == 17
    assert manifest["local_path"] == "source/downloads/example-path.md"
    assert manifest["sha256"].startswith("sha256:")


def test_fetch_public_webpage_falls_back_to_jina_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    responses: list[str] = []

    def fake_urlopen(request, timeout: int = 0):
        responses.append(request.full_url)
        if request.full_url == "https://markdown.new/":
            raise HTTPError(request.full_url, 503, "unavailable", hdrs=None, fp=None)
        return FakeResponse(
            "\n".join(
                [
                    "Title: Example Domain",
                    "",
                    "URL Source: https://example.com/",
                    "",
                    "Markdown Content:",
                    "This is the body.",
                ]
            )
        )

    monkeypatch.setattr(acquisition, "urlopen", fake_urlopen)

    result = acquisition.fetch_public_webpage(
        root=tmp_path / "archive-index",
        source_id="example-fallback",
        source_url="https://example.com/",
    )

    assert responses == ["https://markdown.new/", "https://r.jina.ai/https://example.com/"]
    assert result.provider == "r.jina.ai"
    assert result.local_path.read_text(encoding="utf-8") == "# Example Domain\n\nThis is the body.\n"
    assert result.web_index_result is not None


def test_fetch_public_webpage_rejects_non_http_urls(tmp_path: Path) -> None:
    with pytest.raises(acquisition.SourceCaptureError, match="Unsupported source URL"):
        acquisition.fetch_public_webpage(
            root=tmp_path / "archive-index",
            source_id="local-file",
            source_url="file:///tmp/local.html",
        )
