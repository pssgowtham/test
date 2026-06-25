"""Pydantic data models shared across the pipeline."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FieldStatus(str, Enum):
    ACCEPTED = "accepted"          # confidence high enough, no action
    REMEDIATED = "remediated"      # corrected by Azure OpenAI
    NEEDS_REVIEW = "needs_review"  # still low confidence -> human queue


class ExtractedField(BaseModel):
    name: str
    value: Optional[str] = None
    confidence: float = 0.0
    status: FieldStatus = FieldStatus.ACCEPTED
    # Populated when remediation runs.
    original_value: Optional[str] = None
    remediation_rationale: Optional[str] = None


class StageTiming(BaseModel):
    classify_ms: float = 0.0
    extract_ms: float = 0.0
    remediate_ms: float = 0.0
    total_ms: float = 0.0


class CostBreakdown(BaseModel):
    di_pages: int = 0
    di_cost_usd: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    aoai_cost_usd: float = 0.0
    total_cost_usd: float = 0.0


class RunMetrics(BaseModel):
    run_id: str
    document_type: str
    fields_extracted: int = 0
    fields_remediated: int = 0
    fields_routed_to_review: int = 0
    # Optional accuracy vs. supplied ground truth (fraction of fields matching).
    accuracy: Optional[float] = None
    timing: StageTiming
    cost: CostBreakdown
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RunResult(BaseModel):
    run_id: str
    document_type: str
    accepted_fields: list[ExtractedField]
    routed_fields: list[ExtractedField]
    metrics: RunMetrics


class ReviewItem(BaseModel):
    id: int
    run_id: str
    field_name: str
    extracted_value: Optional[str]
    remediated_value: Optional[str]
    confidence: float
    status: str
    created_at: str
    resolved_value: Optional[str] = None
    resolved_at: Optional[str] = None


class ResolveRequest(BaseModel):
    resolved_value: str
