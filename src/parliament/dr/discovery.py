from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
import re
import unicodedata
from urllib.parse import urljoin


@dataclass(frozen=True)
class DiscoveredAct:
    source_url: str
    source_document_id: str
    source_title: str
    source_date_text: str
    normalized_date: str
    normalized_type: str | None = None
    summary: str | None = None
    observed_facets: dict[str, list[str]] = field(default_factory=dict)
    related_links: dict[str, str] = field(default_factory=dict)
    inferred_metadata: dict[str, str] = field(default_factory=dict)


class _ListingParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.results: list[DiscoveredAct] = []
        self._current: dict[str, object] | None = None
        self._current_link: list[str] = []
        self._current_summary: list[str] = []
        self._current_time: list[str] = []
        self._current_facet_type: str | None = None
        self._current_facet_text: list[str] = []
        self._in_link = False
        self._in_summary = False
        self._in_time = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "article" and attrs_dict.get("class") == "result":
            self._current = {
                "source_document_id": attrs_dict.get("data-id", ""),
                "observed_facets": {},
            }
        elif self._current is not None and tag == "a" and attrs_dict.get("href"):
            self._in_link = True
            self._current["source_url"] = urljoin(self.base_url, attrs_dict["href"])
            self._current_link = []
        elif self._current is not None and tag == "p" and attrs_dict.get("class") == "summary":
            self._in_summary = True
            self._current_summary = []
        elif self._current is not None and tag == "time":
            self._in_time = True
            self._current["normalized_date"] = attrs_dict.get("datetime", "")
            self._current_time = []
        elif self._current is not None and tag == "li" and attrs_dict.get("data-facet-type"):
            self._current_facet_type = attrs_dict["data-facet-type"]
            self._current_facet_text = []

    def handle_endtag(self, tag: str) -> None:
        if self._current is None:
            return
        if tag == "a" and self._in_link:
            self._in_link = False
            self._current["source_title"] = "".join(self._current_link).strip()
        elif tag == "p" and self._in_summary:
            self._in_summary = False
            self._current["summary"] = "".join(self._current_summary).strip()
        elif tag == "time" and self._in_time:
            self._in_time = False
            self._current["source_date_text"] = "".join(self._current_time).strip()
        elif tag == "li" and self._current_facet_type:
            observed_facets = self._current["observed_facets"]
            assert isinstance(observed_facets, dict)
            observed_facets.setdefault(self._current_facet_type, []).append("".join(self._current_facet_text).strip())
            self._current_facet_type = None
            self._current_facet_text = []
        elif tag == "article":
            self.results.append(
                DiscoveredAct(
                    source_url=str(self._current.get("source_url", "")),
                    source_document_id=str(self._current.get("source_document_id", "")),
                    source_title=str(self._current.get("source_title", "")),
                    source_date_text=str(self._current.get("source_date_text", "")),
                    normalized_date=str(self._current.get("normalized_date", "")),
                    summary=str(self._current.get("summary", "")),
                    observed_facets=dict(self._current.get("observed_facets", {})),
                    inferred_metadata={},
                )
            )
            self._current = None

    def handle_data(self, data: str) -> None:
        if self._in_link:
            self._current_link.append(data)
        elif self._in_summary:
            self._current_summary.append(data)
        elif self._in_time:
            self._current_time.append(data)
        elif self._current_facet_type:
            self._current_facet_text.append(data)


class _DetailParser(HTMLParser):
    def __init__(self, source_url: str) -> None:
        super().__init__()
        self.source_url = source_url
        self.title_parts: list[str] = []
        self.summary_parts: list[str] = []
        self.related_links: dict[str, str] = {}
        self.observed_facets: dict[str, list[str]] = {}
        self.normalized_type: str | None = None
        self._in_h1 = False
        self._in_summary = False
        self._in_dt = False
        self._capture_dd = False
        self._last_dt: str | None = None
        self._dd_parts: list[str] = []
        self._facet_type: str | None = None
        self._facet_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "h1":
            self._in_h1 = True
        elif tag == "p" and attrs_dict.get("class") == "sumario":
            self._in_summary = True
        elif tag == "a" and attrs_dict.get("data-rel") and attrs_dict.get("href"):
            self.related_links[attrs_dict["data-rel"]] = urljoin(self.source_url, attrs_dict["href"])
        elif tag == "dt":
            self._in_dt = True
            self._last_dt = ""
        elif tag == "dd":
            self._capture_dd = True
            self._dd_parts = []
        elif tag == "li" and attrs_dict.get("data-facet-type"):
            self._facet_type = attrs_dict["data-facet-type"]
            self._facet_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1":
            self._in_h1 = False
        elif tag == "p" and self._in_summary:
            self._in_summary = False
        elif tag == "dt":
            self._in_dt = False
            if self._last_dt is not None:
                self._last_dt = self._last_dt.strip()
        elif tag == "dd" and self._capture_dd:
            self._capture_dd = False
            if (self._last_dt or "").strip().lower() == "tipo":
                self.normalized_type = "".join(self._dd_parts).strip().lower()
            self._last_dt = None
        elif tag == "li" and self._facet_type:
            self.observed_facets.setdefault(self._facet_type, []).append("".join(self._facet_parts).strip())
            self._facet_type = None

    def handle_data(self, data: str) -> None:
        if self._in_h1:
            self.title_parts.append(data)
        elif self._in_summary:
            self.summary_parts.append(data)
        elif self._in_dt and self._last_dt is not None:
            self._last_dt += data
        elif self._capture_dd:
            self._dd_parts.append(data)
        elif self._facet_type:
            self._facet_parts.append(data)


def parse_legislation_by_date(html: str, *, base_url: str) -> list[DiscoveredAct]:
    parser = _ListingParser(base_url)
    parser.feed(html)
    return parser.results


def parse_act_detail(html: str, *, source_url: str) -> DiscoveredAct:
    parser = _DetailParser(source_url)
    parser.feed(html)
    source_document_id = source_url.rstrip("/").split("-")[-1]
    return DiscoveredAct(
        source_url=source_url,
        source_document_id=source_document_id,
        source_title="".join(parser.title_parts).strip(),
        source_date_text="",
        normalized_date="",
        normalized_type=parser.normalized_type,
        summary="".join(parser.summary_parts).strip(),
        observed_facets=parser.observed_facets,
        related_links=parser.related_links,
        inferred_metadata={},
    )


def discover_recent_acts(
    *,
    listing_html: str,
    fetch_detail_html,
    base_url: str,
    max_acts: int | None = None,
) -> list[DiscoveredAct]:
    discovered = parse_legislation_by_date(listing_html, base_url=base_url)
    if max_acts is not None:
        discovered = discovered[:max_acts]
    enriched: list[DiscoveredAct] = []
    for act in discovered:
        detail = parse_act_detail(fetch_detail_html(act.source_url), source_url=act.source_url)
        enriched.append(
            DiscoveredAct(
                source_url=act.source_url,
                source_document_id=act.source_document_id,
                source_title=detail.source_title or act.source_title,
                source_date_text=act.source_date_text,
                normalized_date=act.normalized_date,
                normalized_type=detail.normalized_type,
                summary=detail.summary or act.summary,
                observed_facets=_merge_facets(act.observed_facets, detail.observed_facets),
                related_links=detail.related_links,
                inferred_metadata={},
            )
        )
    return enriched


def _merge_facets(*facet_maps: dict[str, list[str]]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for facet_map in facet_maps:
        for key, values in facet_map.items():
            bucket = merged.setdefault(key, [])
            for value in values:
                if value not in bucket:
                    bucket.append(value)
    return merged


def discover_acts_from_search_hits(*, hits: list[dict[str, object]], base_url: str) -> list[DiscoveredAct]:
    discovered: list[DiscoveredAct] = []
    for hit in hits:
        source = hit["_source"]
        assert isinstance(source, dict)
        db_id = str(source["dbId"])
        discovered.append(
            DiscoveredAct(
                source_url=_build_detail_url(source, base_url=base_url),
                source_document_id=db_id,
                source_title=str(source.get("title", "")),
                source_date_text=str(source.get("dataPublicacao", "")),
                normalized_date=str(source.get("dataPublicacao", "")),
                normalized_type=_slugify(str(source.get("tipo", ""))) or None,
                summary=_strip_html(str(source.get("sumario", ""))),
                observed_facets=_merge_facets(
                    {"serie": [str(source["serie"])]} if source.get("serie") else {},
                    {"tipo-conteudo": [str(source["tipoConteudo"])]} if source.get("tipoConteudo") else {},
                    {"doc-type": [str(source["docType"])]} if source.get("docType") else {},
                ),
                related_links={},
                inferred_metadata={
                    "db_id": db_id,
                    "file_id": str(source.get("fileId", "")),
                    "numero": str(source.get("numero", "")),
                    "tipo": str(source.get("tipo", "")),
                },
            )
        )
    return discovered


def _build_detail_url(source: dict[str, object], *, base_url: str) -> str:
    tipo = _slugify(str(source.get("tipo", "")))
    numero = _slugify(str(source.get("numero", "")))
    db_id = str(source.get("dbId", ""))
    return f"{base_url}/dr/detalhe/{tipo}/{numero}-{db_id}"


def _strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value).strip()


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
