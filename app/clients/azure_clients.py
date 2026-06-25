"""Construction of Azure SDK clients from application settings.

Clients are created lazily and cached so a single connection pool is reused
across requests.
"""
from __future__ import annotations

from functools import lru_cache

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

from app.config import get_settings


@lru_cache
def get_document_intelligence_client() -> DocumentIntelligenceClient:
    settings = get_settings()
    return DocumentIntelligenceClient(
        endpoint=settings.azure_doc_intelligence_endpoint,
        credential=AzureKeyCredential(settings.azure_doc_intelligence_key),
    )


@lru_cache
def get_openai_client() -> AzureOpenAI:
    settings = get_settings()
    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )
