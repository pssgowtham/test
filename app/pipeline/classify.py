"""Document classification stage.

Uses Azure Document Intelligence's prebuilt read model to obtain document text,
then applies lightweight keyword heuristics to decide the document type and the
DI model that the extraction stage should use. This keeps a clear seam where a
trained custom classifier could later be plugged in.
"""
from __future__ import annotations

from azure.ai.documentintelligence.models import AnalyzeResult

from app.clients.azure_clients import get_document_intelligence_client

# document_type -> DI model id used for extraction
MODEL_ROUTING = {
    "invoice": "prebuilt-invoice",
    "receipt": "prebuilt-receipt",
    "unknown": "prebuilt-invoice",
}


def classify(document_bytes: bytes) -> tuple[str, str]:
    """Return (document_type, di_model_id) for the supplied document."""
    client = get_document_intelligence_client()
    poller = client.begin_analyze_document("prebuilt-read", body=document_bytes)
    result: AnalyzeResult = poller.result()
    text = (result.content or "").lower()

    if "invoice" in text or "invoice number" in text or "bill to" in text:
        doc_type = "invoice"
    elif "receipt" in text or "subtotal" in text and "merchant" in text:
        doc_type = "receipt"
    else:
        doc_type = "unknown"

    return doc_type, MODEL_ROUTING[doc_type]
