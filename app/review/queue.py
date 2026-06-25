"""Human review queue backed by SQLite.

Fields that stay below the review threshold are enqueued here for a human to
correct. The queue is intentionally simple (single table) and self-initializing.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from app.config import get_settings
from app.models import ExtractedField, ReviewItem

_SCHEMA = """
CREATE TABLE IF NOT EXISTS review_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    extracted_value TEXT,
    remediated_value TEXT,
    confidence REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    resolved_value TEXT,
    resolved_at TEXT
);
"""


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    path = Path(get_settings().review_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def enqueue(run_id: str, fields: list[ExtractedField]) -> int:
    """Insert routed fields into the queue. Returns the number enqueued."""
    if not fields:
        return 0
    now = datetime.utcnow().isoformat()
    with _connect() as conn:
        conn.executemany(
            """INSERT INTO review_items
               (run_id, field_name, extracted_value, remediated_value,
                confidence, status, created_at)
               VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
            [
                (
                    run_id,
                    f.name,
                    f.original_value if f.original_value is not None else f.value,
                    f.value,
                    f.confidence,
                    now,
                )
                for f in fields
            ],
        )
    return len(fields)


def list_pending() -> list[ReviewItem]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM review_items WHERE status = 'pending' ORDER BY created_at"
        ).fetchall()
    return [ReviewItem(**dict(row)) for row in rows]


def resolve(item_id: int, resolved_value: str) -> bool:
    """Mark a review item resolved. Returns False if the item does not exist."""
    now = datetime.utcnow().isoformat()
    with _connect() as conn:
        cur = conn.execute(
            """UPDATE review_items
               SET status = 'resolved', resolved_value = ?, resolved_at = ?
               WHERE id = ? AND status = 'pending'""",
            (resolved_value, now, item_id),
        )
        return cur.rowcount > 0
