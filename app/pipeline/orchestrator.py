"""Pipeline orchestration: wire the stages together for a single document run.

Flow: classify -> extract -> remediate -> threshold -> route to review,
capturing per-stage latency and cost, and emitting a metrics record.
"""
from __future__ import annotations

import time
import uuid
from typing import Optional

from app.models import (
    CostBreakdown,
    ExtractedField,
    RunMetrics,
    RunResult,
    StageTiming,
)
from app.observability import metrics as metrics_log
from app.observability.cost import estimate_cost
from app.pipeline import classify as classify_stage
from app.pipeline import extract as extract_stage
from app.pipeline import remediate as remediate_stage
from app.pipeline.threshold import apply_threshold
from app.review import queue as review_queue


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000.0, 2)


def _accuracy(
    fields: list[ExtractedField], ground_truth: dict[str, str]
) -> Optional[float]:
    """Fraction of ground-truth fields whose extracted value matches."""
    if not ground_truth:
        return None
    by_name = {f.name: (f.value or "") for f in fields}
    matches = sum(
        1
        for name, expected in ground_truth.items()
        if by_name.get(name, "").strip() == str(expected).strip()
    )
    return round(matches / len(ground_truth), 4)


def run_document(
    document_bytes: bytes,
    ground_truth: Optional[dict[str, str]] = None,
) -> RunResult:
    run_id = str(uuid.uuid4())
    total_start = time.perf_counter()

    # 1. Classify
    t = time.perf_counter()
    doc_type, model_id = classify_stage.classify(document_bytes)
    classify_ms = _ms(t)

    # 2. Extract
    t = time.perf_counter()
    fields, page_count, document_text = extract_stage.extract(document_bytes, model_id)
    extract_ms = _ms(t)

    # 3. Remediate low-confidence fields
    t = time.perf_counter()
    fields, prompt_tokens, completion_tokens = remediate_stage.remediate(
        fields, document_text
    )
    remediate_ms = _ms(t)

    # 4. Threshold + 5. Route
    accepted, routed = apply_threshold(fields)
    routed_count = review_queue.enqueue(run_id, routed)

    # 6. Observe
    cost: CostBreakdown = estimate_cost(
        di_pages=page_count,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    timing = StageTiming(
        classify_ms=classify_ms,
        extract_ms=extract_ms,
        remediate_ms=remediate_ms,
        total_ms=_ms(total_start),
    )
    run_metrics = RunMetrics(
        run_id=run_id,
        document_type=doc_type,
        fields_extracted=len(fields),
        fields_remediated=sum(1 for f in fields if f.original_value is not None),
        fields_routed_to_review=routed_count,
        accuracy=_accuracy(fields, ground_truth or {}),
        timing=timing,
        cost=cost,
    )
    metrics_log.log_run(run_metrics)

    return RunResult(
        run_id=run_id,
        document_type=doc_type,
        accepted_fields=accepted,
        routed_fields=routed,
        metrics=run_metrics,
    )
