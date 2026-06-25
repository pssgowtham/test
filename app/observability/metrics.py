"""Per-run metrics logging.

Each run appends one JSON object to a JSONL file so the data can be tailed,
shipped to a log aggregator, or read back via the API for monitoring.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from app.config import get_settings
from app.models import RunMetrics


def log_run(metrics: RunMetrics) -> None:
    path = Path(get_settings().metrics_log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(metrics.model_dump_json() + "\n")


def read_runs(limit: int = 50) -> list[dict]:
    """Return the most recent run metric records (newest last)."""
    path = Path(get_settings().metrics_log_path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        lines = [line for line in fh if line.strip()]
    records = [json.loads(line) for line in lines[-limit:]]
    return records
