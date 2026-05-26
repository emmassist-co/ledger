from __future__ import annotations

from parliament.models.document import ExtractedPage


def build_page_map(pages: list[ExtractedPage]) -> dict[str, object]:
    document_id = pages[0].document_id if pages else ""
    return {
        "document_id": document_id,
        "pages": [
            {
                "page_number": page.page_number,
                "text": page.markdown,
            }
            for page in pages
        ],
    }
