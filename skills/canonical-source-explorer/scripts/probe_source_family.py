from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from typing import Iterable


DEFAULT_TIMEOUT = 15.0
DEFAULT_READ_LIMIT = 200_000


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.script_count = 0
        self.visible_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag == "a" and attr_map.get("href"):
            self.links.append(attr_map["href"] or "")
        elif tag == "script":
            self.script_count += 1

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text:
            self.visible_text.append(text)


@dataclass
class ProbeReport:
    url: str
    final_url: str
    status_code: int
    content_type: str
    source_shape: str
    recommended_acquisition_mode: str
    retrieval_unit: str
    browser_escalation_allowed: bool
    canonicality_guess: str
    notes: list[str]
    adjacent_surface_hints: list[str]
    metrics: dict[str, int]


def fetch(url: str, timeout: float, read_limit: int) -> tuple[str, str, int, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ledger-canonical-source-explorer/0.1",
            "Accept": "text/html,application/xml,application/rss+xml,application/pdf,*/*;q=0.8",
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        body_bytes = response.read(read_limit)
        charset = response.headers.get_content_charset() or "utf-8"
        body = body_bytes.decode(charset, errors="replace")
        return response.geturl(), content_type, response.status, body


def classify(url: str, final_url: str, status_code: int, content_type: str, body: str) -> ProbeReport:
    parsed = urllib.parse.urlparse(final_url)
    path = parsed.path.lower()
    content_type_lower = content_type.lower()
    notes: list[str] = []
    hints: list[str] = []
    metrics: dict[str, int] = {}

    if ".pdf" in path or "application/pdf" in content_type_lower:
        return ProbeReport(
            url=url,
            final_url=final_url,
            status_code=status_code,
            content_type=content_type,
            source_shape="direct_pdf",
            recommended_acquisition_mode="preserve_raw_pdf_then_extract_and_index",
            retrieval_unit="pdf_page",
            browser_escalation_allowed=False,
            canonicality_guess="high",
            notes=["Direct PDF surface detected."],
            adjacent_surface_hints=[],
            metrics=metrics,
        )

    body_lstrip = body.lstrip().lower()
    if "xml" in content_type_lower or body_lstrip.startswith("<?xml"):
        if "<rss" in body_lstrip or "<feed" in body_lstrip or "<channel>" in body_lstrip:
            hints.extend(infer_feed_hints(final_url))
            return ProbeReport(
                url=url,
                final_url=final_url,
                status_code=status_code,
                content_type=content_type,
                source_shape="rss_feed",
                recommended_acquisition_mode="sync_registry_then_promote_linked_documents",
                retrieval_unit="feed_item",
                browser_escalation_allowed=False,
                canonicality_guess="high",
                notes=["Feed surface detected."],
                adjacent_surface_hints=dedupe(hints),
                metrics=metrics,
            )
        return ProbeReport(
            url=url,
            final_url=final_url,
            status_code=status_code,
            content_type=content_type,
            source_shape="structured_xml",
            recommended_acquisition_mode="preserve_raw_xml_then_derive_registry_or_extract_units",
            retrieval_unit="xml_record",
            browser_escalation_allowed=False,
            canonicality_guess="medium",
            notes=["Structured XML surface detected."],
            adjacent_surface_hints=[],
            metrics=metrics,
        )

    parser = LinkCollector()
    parser.feed(body)
    visible_text = " ".join(parser.visible_text)
    link_count = len(parser.links)
    script_count = parser.script_count
    text_length = len(visible_text)
    metrics.update(
        {
            "link_count": link_count,
            "script_count": script_count,
            "text_length": text_length,
        }
    )

    if "/legislacao-consolidada/" in path:
        notes.append("Path pattern suggests a consolidated legal view.")
        hints.extend(collect_pdf_hints(parser.links, final_url))
        return ProbeReport(
            url=url,
            final_url=final_url,
            status_code=status_code,
            content_type=content_type,
            source_shape="consolidated_legal_view",
            recommended_acquisition_mode="treat_as_currentness_sensitive_canonical_view_and_pair_with_raw_sources_when_possible",
            retrieval_unit="article_or_section",
            browser_escalation_allowed=False,
            canonicality_guess="high",
            notes=notes,
            adjacent_surface_hints=dedupe(hints),
            metrics=metrics,
        )

    if "/detalhe/" in path:
        notes.append("Path pattern suggests a canonical detail page.")
        hints.extend(collect_pdf_hints(parser.links, final_url))
        return ProbeReport(
            url=url,
            final_url=final_url,
            status_code=status_code,
            content_type=content_type,
            source_shape="canonical_detail_page",
            recommended_acquisition_mode="capture_canonical_pointer_and_pair_with_raw_download_surface",
            retrieval_unit="document",
            browser_escalation_allowed=False,
            canonicality_guess="high",
            notes=notes,
            adjacent_surface_hints=dedupe(hints),
            metrics=metrics,
        )

    if looks_like_app_shell(body, script_count, text_length):
        notes.append("HTML looks like an app shell with little user-facing content.")
        hints.extend(infer_shell_hints(final_url))
        return ProbeReport(
            url=url,
            final_url=final_url,
            status_code=status_code,
            content_type=content_type,
            source_shape="app_shell",
            recommended_acquisition_mode="do_not_treat_shell_assets_as_sources_probe_for_feeds_files_or_stable_detail_surfaces_first",
            retrieval_unit="none",
            browser_escalation_allowed=True,
            canonicality_guess="low",
            notes=notes,
            adjacent_surface_hints=dedupe(hints),
            metrics=metrics,
        )

    if link_count >= 10:
        notes.append("HTML exposes enough links to behave like a listing page.")
        hints.extend(collect_pdf_hints(parser.links, final_url))
        return ProbeReport(
            url=url,
            final_url=final_url,
            status_code=status_code,
            content_type=content_type,
            source_shape="listing_page",
            recommended_acquisition_mode="capture_markdown_or_html_then_extract_canonical_child_links",
            retrieval_unit="listing_item",
            browser_escalation_allowed=False,
            canonicality_guess="medium",
            notes=notes,
            adjacent_surface_hints=dedupe(hints),
            metrics=metrics,
        )

    return ProbeReport(
        url=url,
        final_url=final_url,
        status_code=status_code,
        content_type=content_type,
        source_shape="general_html_page",
        recommended_acquisition_mode="capture_clean_page_then_reassess_adjacent_canonical_surfaces",
        retrieval_unit="page",
        browser_escalation_allowed=False,
        canonicality_guess="unknown",
        notes=["No stronger canonical source shape was inferred from the cheap probe."],
        adjacent_surface_hints=dedupe(collect_pdf_hints(parser.links, final_url)),
        metrics=metrics,
    )


def infer_feed_hints(url: str) -> list[str]:
    parsed = urllib.parse.urlparse(url)
    hints = []
    if parsed.netloc.endswith("files.diariodarepublica.pt"):
        if "serie1" in parsed.path:
            hints.append("paired_html_or_pdf_feed_variant_for_serie1")
        if "serie2" in parsed.path:
            hints.append("paired_html_or_pdf_feed_variant_for_serie2")
    return hints


def infer_shell_hints(url: str) -> list[str]:
    parsed = urllib.parse.urlparse(url)
    hints = []
    if "diariodarepublica.pt" in parsed.netloc:
        hints.extend(
            [
                "check_files_host_for_rss_or_pdf_surfaces",
                "check_dr_detail_and_consolidated_url_families",
            ]
        )
    return hints


def collect_pdf_hints(links: Iterable[str], base_url: str) -> list[str]:
    hints: list[str] = []
    for link in links:
        resolved = urllib.parse.urljoin(base_url, link)
        lower = resolved.lower()
        if lower.endswith(".pdf"):
            hints.append(resolved)
    return hints[:10]


def looks_like_app_shell(body: str, script_count: int, text_length: int) -> bool:
    lower = body.lower()
    signals = [
        "javascript is required" in lower,
        "reactcontainer" in lower,
        "outsystemsapp" in lower,
    ]
    return script_count >= 3 and text_length < 300 and any(signals)


def dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        cleaned = item.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="probe_source_family")
    parser.add_argument("url")
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--read-limit", type=int, default=DEFAULT_READ_LIMIT)
    args = parser.parse_args(argv)

    try:
        final_url, content_type, status_code, body = fetch(args.url, args.timeout, args.read_limit)
        report = classify(args.url, final_url, status_code, content_type, body)
    except urllib.error.HTTPError as exc:
        report = ProbeReport(
            url=args.url,
            final_url=exc.geturl(),
            status_code=exc.code,
            content_type=exc.headers.get("Content-Type", ""),
            source_shape="error",
            recommended_acquisition_mode="retry_or_escalate_after_manual_review",
            retrieval_unit="unknown",
            browser_escalation_allowed=True,
            canonicality_guess="unknown",
            notes=[f"HTTP error during probe: {exc.code}"],
            adjacent_surface_hints=[],
            metrics={},
        )
    except Exception as exc:  # noqa: BLE001
        report = ProbeReport(
            url=args.url,
            final_url=args.url,
            status_code=0,
            content_type="",
            source_shape="error",
            recommended_acquisition_mode="retry_or_escalate_after_manual_review",
            retrieval_unit="unknown",
            browser_escalation_allowed=True,
            canonicality_guess="unknown",
            notes=[f"Probe failed: {exc}"],
            adjacent_surface_hints=[],
            metrics={},
        )

    payload = asdict(report)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
