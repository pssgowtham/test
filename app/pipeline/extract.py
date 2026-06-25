"""Field extraction stage using Azure Document Intelligence.

Runs a prebuilt model over the document and flattens the recognized document
fields into a list of ExtractedField objects carrying per-field confidence.
"""
from __future__ import annotations

from typing import Optional

from azure.ai.documentintelligence.models import AnalyzeResult

from app.clients.azure_clients import get_document_intelligence_client
from app.models import ExtractedField


def _field_to_str(field) -> Optional[str]:
    """Best-effort string rendering of a DI field value."""
    if field is None:
        return None
    for attr in (
        "value_string",
        "value_number",
        "value_date",
        "value_currency",
        "value_address",
        "value_phone_number",
        "content",
    ):
        val = getattr(field, attr, None)
        if val is not None:
            # value_currency is an object; render its amount when present.
            amount = getattr(val, "amount", None)
            return str(amount) if amount is not None else str(val)
    return None


def extract(
    document_bytes: bytes, model_id: str
) -> tuple[list[ExtractedField], int, str]:
    """Return (fields, page_count, document_text) extracted from the document."""
    client = get_document_intelligence_client()
    poller = client.begin_analyze_document(model_id, body=document_bytes)
    result: AnalyzeResult = poller.result()

    page_count = len(result.pages) if result.pages else 1
    document_text = result.content or ""
    fields: list[ExtractedField] = []

    documents = result.documents or []
    for doc in documents:
        for name, field in (doc.fields or {}).items():
            fields.append(
                ExtractedField(
                    name=name,
                    value=_field_to_str(field),
                    confidence=float(getattr(field, "confidence", 0.0) or 0.0),
                )
            )
    return fields, page_count, document_text
