"""AI remediation stage using Azure OpenAI.

Low-confidence fields are sent to the model together with the raw document text
so it can validate and, where possible, correct the values. The model returns
structured JSON so results parse deterministically.
"""
from __future__ import annotations

import json
from typing import Optional

from app.clients.azure_clients import get_openai_client
from app.config import get_settings
from app.models import ExtractedField, FieldStatus

SYSTEM_PROMPT = (
    "You are a data-extraction quality assistant. You are given the raw text of "
    "a document and a list of fields that were extracted with low confidence. "
    "For each field, validate the value against the document text and correct it "
    "if it is wrong. Respond ONLY with JSON matching the requested schema. For "
    "each field return: name, corrected_value (string or null if not present), "
    "confidence (0..1, your confidence in corrected_value), and rationale (short)."
)


def _build_user_prompt(document_text: str, fields: list[ExtractedField]) -> str:
    payload = [
        {"name": f.name, "extracted_value": f.value, "confidence": f.confidence}
        for f in fields
    ]
    return (
        f"DOCUMENT TEXT:\n{document_text[:12000]}\n\n"
        f"LOW CONFIDENCE FIELDS:\n{json.dumps(payload, indent=2)}\n\n"
        'Return JSON of the form: {"fields": [{"name": ..., "corrected_value": ..., '
        '"confidence": ..., "rationale": ...}]}'
    )


def remediate(
    fields: list[ExtractedField], document_text: str
) -> tuple[list[ExtractedField], int, int]:
    """Validate/correct low-confidence fields.

    Returns (updated_fields, prompt_tokens, completion_tokens). Fields at or
    above the remediation threshold are returned unchanged.
    """
    settings = get_settings()
    threshold = settings.remediation_threshold

    low = [f for f in fields if f.confidence < threshold]
    if not low:
        return fields, 0, 0

    client = get_openai_client()
    response = client.chat.completions.create(
        model=settings.azure_openai_deployment,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(document_text, low)},
        ],
    )

    prompt_tokens = response.usage.prompt_tokens if response.usage else 0
    completion_tokens = response.usage.completion_tokens if response.usage else 0

    corrections: dict[str, dict] = {}
    try:
        parsed = json.loads(response.choices[0].message.content or "{}")
        for item in parsed.get("fields", []):
            corrections[item["name"]] = item
    except (json.JSONDecodeError, KeyError, TypeError):
        # On a malformed model response, leave fields untouched; thresholding
        # will route them to human review.
        corrections = {}

    for f in fields:
        if f.name not in corrections:
            continue
        c = corrections[f.name]
        new_conf = float(c.get("confidence", f.confidence) or 0.0)
        new_value: Optional[str] = c.get("corrected_value")
        f.original_value = f.value
        f.value = str(new_value) if new_value is not None else None
        f.confidence = new_conf
        f.remediation_rationale = c.get("rationale")
        f.status = FieldStatus.REMEDIATED

    return fields, prompt_tokens, completion_tokens
