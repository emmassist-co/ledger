from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from functools import cached_property
from typing import Any
from urllib.request import urlopen


ANONYMOUS_CSRF_TOKEN = "T6C+9iB49TLra4jEsMeSckDMNhQ="
MODULE_INFO_URL = "https://diariodarepublica.pt/dr/moduleservices/moduleinfo?dr"
SEARCH_RESULTS_API_VERSION = "PRsQKjEXDVBC3ZSqkS8k6A"
SCREEN_VIEW_NAME = "Pesquisas.PesquisaResultado"
RESULTS_PER_PAGE = 25


@dataclass(frozen=True)
class DrLegislationDetail:
    source_url: str
    source_document_id: str
    source_title: str
    publication_text: str
    number: str
    normalized_type: str
    summary: str
    full_text: str


@dataclass(frozen=True)
class DrConsolidatedArticle:
    number: str
    heading: str
    text: str


@dataclass(frozen=True)
class DrConsolidatedDocument:
    source_url: str
    title: str
    formatted_title: str
    note: str
    eli_html_url: str
    eli_pdf_url: str
    articles: list[DrConsolidatedArticle] = field(default_factory=list)


class DrClient:
    def fetch_text(self, url: str) -> str:
        with urlopen(url) as response:  # noqa: S310
            return response.read().decode("utf-8")

    @cached_property
    def module_version(self) -> str:
        payload = json.loads(self.fetch_text(MODULE_INFO_URL))
        return str(payload["manifest"]["versionToken"])

    def fetch_json(self, url: str) -> dict[str, Any]:
        return json.loads(self.fetch_text(url))

    def search_recent_legislation(self, *, max_acts: int) -> list[dict[str, Any]]:
        today = datetime.now(UTC).date()
        start = date(today.year - 1, 1, 1)
        return self.search_legislation(
            date_from=start.isoformat(),
            date_to=today.isoformat(),
            max_acts=max_acts,
        )

    def search_legislation(self, *, date_from: str, date_to: str, max_acts: int) -> list[dict[str, Any]]:
        hits: list[dict[str, Any]] = []
        seen_ids: set[int] = set()
        start_index = 0
        while len(hits) < max_acts:
            payload = self._post_data_action(
                endpoint="https://diariodarepublica.pt/dr/screenservices/dr/Pesquisas/PesquisaResultado/DataActionGetPesquisas",
                api_version=SEARCH_RESULTS_API_VERSION,
                view_name=SCREEN_VIEW_NAME,
                variables=_build_search_variables(date_from=date_from, date_to=date_to, start_index=start_index),
            )
            result_blob = payload["data"]["Resultado"]
            result_data = json.loads(result_blob)
            page_hits = result_data["hits"]["hits"]
            if not page_hits:
                break
            for hit in page_hits:
                source = hit["_source"]
                db_id = int(source["dbId"])
                if db_id in seen_ids:
                    continue
                seen_ids.add(db_id)
                hits.append(hit)
                if len(hits) >= max_acts:
                    break
            start_index += RESULTS_PER_PAGE
            if len(page_hits) < RESULTS_PER_PAGE:
                break
        return hits

    def fetch_legislation_detail(
        self,
        *,
        source_url: str,
        content_id: str,
        number_slug: str,
        year: int,
        tipo: str,
    ) -> DrLegislationDetail:
        payload = self._post_data_action(
            endpoint="https://diariodarepublica.pt/dr/screenservices/dr/Legislacao_Conteudos/Conteudo_Detalhe/DataActionGetConteudoData",
            api_version="bS76NLB99XmLsd9FrJKHLw",
            view_name="Legislacao_Conteudos.Conteudo_Detalhe",
            variables=_build_detail_variables(
                content_id=content_id,
                number_slug=number_slug,
                year=year,
                tipo=tipo,
                key=_detail_key(source_url),
            ),
        )
        detail = payload["data"]["DetalheConteudo"]
        return DrLegislationDetail(
            source_url=source_url,
            source_document_id=content_id,
            source_title=str(detail.get("Titulo", "")).strip(),
            publication_text=str(detail.get("Publicacao", "")).strip(),
            number=str(detail.get("Numero", "")).strip(),
            normalized_type=tipo,
            summary=str(detail.get("Sumario", "")).strip(),
            full_text=str(detail.get("Texto", "")).strip(),
        )

    def fetch_consolidated_document(
        self,
        *,
        source_url: str,
        diploma_frag_id: str,
        year: int,
        tipo: str,
    ) -> DrConsolidatedDocument:
        metadata_payload = self._post_data_action(
            endpoint="https://diariodarepublica.pt/dr/screenservices/dr/LegislacaoConsolidada/LegCons_Detalhe/DataActionGetDiplomaFragByIdAndApplicationSetting",
            api_version="eKEmFqPenfyckjMC3ozldQ",
            view_name="LegislacaoConsolidada.LegCons_Detalhe",
            variables=_build_consolidated_variables(
                diploma_frag_id=diploma_frag_id,
                year=year,
                tipo=tipo,
                key=_consolidated_key(source_url),
            ),
        )
        frag = metadata_payload["data"]["ConsolidadaConteudoDetalhe"]["DiplomaFrag"]
        eli_html_url = str(frag.get("ELI", "")).strip()
        eli_pdf_url = _derive_eli_pdf_url(eli_html_url)
        return DrConsolidatedDocument(
            source_url=source_url,
            title=str(frag.get("Designacao", "")).strip(),
            formatted_title=str(frag.get("FormattedTitle", "")).strip(),
            note=str(frag.get("Nota", "")).strip(),
            eli_html_url=eli_html_url,
            eli_pdf_url=eli_pdf_url,
            articles=[],
        )

    def _post_data_action(
        self,
        *,
        endpoint: str,
        api_version: str,
        view_name: str,
        variables: dict[str, Any],
        input_parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from urllib.request import Request

        body: dict[str, Any] = {
            "versionInfo": {
                "moduleVersion": self.module_version,
                "apiVersion": api_version,
            },
            "viewName": view_name,
            "screenData": {
                "variables": variables,
            },
        }
        if input_parameters is not None:
            body["inputParameters"] = input_parameters
        payload = json.dumps(body, separators=(",", ":")).encode("utf-8")
        request = Request(
            endpoint,
            data=payload,
            headers={
                "Content-Type": "application/json; charset=UTF-8",
                "Accept": "application/json",
                "X-CSRFToken": ANONYMOUS_CSRF_TOKEN,
            },
            method="POST",
        )
        with urlopen(request) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))


def _build_search_variables(*, date_from: str, date_to: str, start_index: int) -> dict[str, Any]:
    return {
        "FiltrosDePesquisa": {
            "tipoConteudo": {"List": ["AtosSerie1", "AtosSerie2", "AtosSocietarios"]},
            "serie": {"List": ["I", "II"]},
            "numero": "",
            "ano": "0",
            "suplemento": "0",
            "dataPublicacao": "",
            "dataPublicacaoDe": date_from,
            "dataPublicacaoAte": date_to,
            "parte": "",
            "apendice": "",
            "fasciculo": "",
            "tipo": {"List": [], "EmptyListItem": ""},
            "emissor": {"List": [], "EmptyListItem": ""},
            "texto": "",
            "sumario": "",
            "entidadeProponente": {"List": [], "EmptyListItem": ""},
            "numeroDR": "",
            "paginaInicial": "0",
            "paginaFinal": "0",
            "dataAssinatura": "",
            "dataDistribuicao": "",
            "entidadePrincipal": {"List": [], "EmptyListItem": ""},
            "entidadeEmitente": {"List": [], "EmptyListItem": ""},
            "docType": "",
            "proferido": "",
            "processo": "",
            "assunto": "",
            "recorrente": "",
            "recorrido": "",
            "relator": "",
            "empresa": "",
            "concelho": "",
            "nif": "",
            "anuncio": "",
            "numeroDoc": "",
            "DataAssinaturaDe": "1900-01-01",
            "DataAssinaturaAte": "1900-01-01",
            "DataDistribuicaoDe": "1900-01-01",
            "DataDistribuicaoAte": "1900-01-01",
            "semestre": "",
            "IsLegConsolidadaSelected": False,
            "IsFromData": True,
            "DescritorList": {"List": [], "EmptyListItem": ""},
        },
        "ResultadosPorPaginaId": 4,
        "StartIndex": start_index,
        "TipoOrdenacaoId": 4,
        "Ordenacoes": {
            "List": [
                {"Field": "dataPublicacao", "Order": "desc"},
                {"Field": "numeroDR.keyword", "Order": "desc"},
                {"Field": "serieNR", "Order": "asc"},
                {"Field": "suplemento", "Order": "asc"},
                {"Field": "apendice.keyword", "Order": "asc"},
            ]
        },
    }


def _build_detail_variables(*, content_id: str, number_slug: str, year: int, tipo: str, key: str) -> dict[str, Any]:
    return {
        "DipLegisId": content_id,
        "ConteudoId": content_id,
        "Numero": number_slug,
        "Year": year,
        "Tipo": tipo,
        "Key": key,
        "MostrarNoRegistoDeAlteracoes": False,
        "ContainsTable": False,
        "ContainsQuote": False,
        "ContainsEditLink": False,
        "NotExists": False,
        "NotVisible": False,
        "NotData": False,
        "TextoPesquisa": "",
        "ExternalPesquisaLink": "",
        "LinkRevistaLink": "",
        "IsConsolidada": False,
        "ConteudoDetalhe": {"Data": "1900-01-01", "Id": "0", "Title": "", "SubTitle": "", "Description": "", "Author": "", "Keywords": ""},
        "ApplicationSettings": {"ValueInt": "", "ValueBoolean": False, "Name": ""},
        "ErrorText": "",
        "JsonLd": "",
        "PaginaEmModoSelo": False,
        "SchemaOrg": {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": "",
            "image": "",
            "datePublished": "1900-01-01",
            "dateModified": "1900-01-01",
            "author": {"@type": "Person", "name": ""},
            "publisher": {"@type": "Organization", "name": "", "logo": {"@type": "ImageObject", "url": ""}},
            "description": "",
            "mainEntityOfPage": {"@type": "WebPage", "@id": ""},
        },
        "CurrentTab": "tab1",
        "Tabs": {"List": []},
        "LinkPublicacao": False,
        "SideContentData": {
            "TooltipMessage": "",
            "Links": {"List": []},
            "MostrarConsultarPublicacao": False,
            "PubContent": {"PubFileId": "", "PubHash": "", "PubDate": "1900-01-01", "PubNr": "", "PubSerie": "", "PubSupp": "", "PubPdf": ""},
        },
        "SourceFile": "",
        "VisibleContent": "",
        "DataSelecionada": "2026-05-23",
    }


def _build_consolidated_variables(*, diploma_frag_id: str, year: int, tipo: str, key: str) -> dict[str, Any]:
    return {
        "DiplomaFragId": diploma_frag_id,
        "Ano": year,
        "Key": key,
        "Tipo": tipo,
        "TextoPesquisa": "",
        "ContainsTable": False,
        "ContainsQuote": False,
        "ContainsEditLink": False,
        "NotExists": False,
        "NotVisible": False,
        "NotData": False,
        "VisibleContent": "",
        "PaginaEmModoSelo": False,
        "ConsolidadaConteudoDetalhe": {"Data": "1900-01-01", "Id": "0", "Title": "", "SubTitle": "", "Description": "", "Author": "", "Keywords": ""},
        "ApplicationSettings": {"ValueInt": "", "ValueBoolean": False, "Name": ""},
        "ErrorText": "",
        "JsonLd": "",
        "CurrentTab": "tab1",
        "Tabs": {"List": []},
        "CurrentVersionsTab": "tab1",
        "VersionsTabs": {"List": []},
        "IsConsolidada": True,
        "HeaderLinksEmpty": False,
        "SideContentData": {
            "TooltipMessage": "",
            "Links": {"List": []},
            "MostrarConsultarPublicacao": False,
            "PubContent": {"PubFileId": "", "PubHash": "", "PubDate": "1900-01-01", "PubNr": "", "PubSerie": "", "PubSupp": "", "PubPdf": ""},
        },
        "DataSelecionada": "2026-05-23",
    }


def _detail_key(source_url: str) -> str:
    return source_url.rstrip("/").split("/")[-1]


def _consolidated_key(source_url: str) -> str:
    return source_url.rstrip("/").split("/")[-1]
def _derive_eli_pdf_url(eli_html_url: str) -> str:
    if eli_html_url.endswith("/html"):
        return f"{eli_html_url[:-5]}/pdf"
    return eli_html_url
