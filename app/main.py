"""FastAPI application exposing the invoice processing pipeline."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from app.config import get_settings
from app.models import ResolveRequest, ReviewItem, RunResult
from app.observability import metrics as metrics_log
from app.pipeline import orchestrator
from app.review import queue as review_queue

app = FastAPI(
    title="Azure Invoice Processing Pipeline",
    description=(
        "Classifies a document, extracts fields with Azure Document "
        "Intelligence, remediates low-confidence fields with Azure OpenAI, and "
        "routes residual low-confidence fields to a human review queue."
    ),
    version="1.0.0",
)


@app.get("/health")
def health() -> dict:
    """Liveness + configuration validation. Reports which Azure settings are
    missing rather than crashing, so operators get an actionable message."""
    try:
        get_settings()
        return {"status": "ok", "config": "valid"}
    except ValidationError as exc:
        missing = [e["loc"][0] for e in exc.errors()]
        return {"status": "degraded", "config": "invalid", "missing": missing}


@app.post("/process", response_model=RunResult)
async def process(
    file: UploadFile = File(...),
    ground_truth: Optional[str] = Form(
        None, description="Optional JSON object of field_name -> expected value"
    ),
) -> RunResult:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    gt: dict[str, str] = {}
    if ground_truth:
        try:
            gt = json.loads(ground_truth)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="ground_truth must be valid JSON."
            )

    try:
        return orchestrator.run_document(content, ground_truth=gt)
    except Exception as exc:  # surface Azure SDK errors as 502
        raise HTTPException(status_code=502, detail=f"Pipeline error: {exc}") from exc


@app.get("/review", response_model=list[ReviewItem])
def list_review() -> list[ReviewItem]:
    return review_queue.list_pending()


@app.post("/review/{item_id}/resolve")
def resolve_review(item_id: int, body: ResolveRequest) -> dict:
    ok = review_queue.resolve(item_id, body.resolved_value)
    if not ok:
        raise HTTPException(
            status_code=404, detail="Review item not found or already resolved."
        )
    return {"status": "resolved", "id": item_id}


@app.get("/metrics/runs")
def metrics_runs(limit: int = 50) -> list[dict]:
    return metrics_log.read_runs(limit=limit)
