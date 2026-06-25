"""Confidence thresholding stage.

Splits fields into those accepted automatically and those that must be routed
to a human review queue because their (post-remediation) confidence is still
below the review threshold.
"""
from __future__ import annotations

from app.config import get_settings
from app.models import ExtractedField, FieldStatus


def apply_threshold(
    fields: list[ExtractedField],
) -> tuple[list[ExtractedField], list[ExtractedField]]:
    """Return (accepted_fields, routed_fields)."""
    review_threshold = get_settings().review_threshold
    accepted: list[ExtractedField] = []
    routed: list[ExtractedField] = []

    for f in fields:
        if f.confidence < review_threshold:
            f.status = FieldStatus.NEEDS_REVIEW
            routed.append(f)
        else:
            accepted.append(f)
    return accepted, routed
