"""SQLite sink with idempotent writes (INSERT OR IGNORE on event_id PK)."""

import os
import sqlite3

from src.config import DB_PATH
from src.logger import get_logger

logger = get_logger("sink")


def init_db(db_path: str | None = None) -> sqlite3.Connection:
    """Create (or open) the telemetry_events table and return a connection."""
    path = db_path or DB_PATH
    if path != ":memory:":
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry_events (
            event_id    TEXT PRIMARY KEY,
            device_id   TEXT    NOT NULL,
            zone        TEXT    NOT NULL,
            ts          REAL    NOT NULL,
            kpi         TEXT    NOT NULL,
            value       REAL    NOT NULL,
            is_degraded INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def write_event(conn: sqlite3.Connection, record: dict) -> bool:
    """Insert a processed event.  Returns True if inserted, False if duplicate.

    Idempotency is guaranteed by ``INSERT OR IGNORE`` on the ``event_id``
    primary key – re-processing the same event is a safe no-op.
    """
    try:
        before = conn.total_changes
        conn.execute(
            """
            INSERT OR IGNORE INTO telemetry_events
                (event_id, device_id, zone, ts, kpi, value, is_degraded)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["event_id"],
                record["device_id"],
                record["zone"],
                record["ts"],
                record["kpi"],
                record["value"],
                int(record["is_degraded"]),
            ),
        )
        conn.commit()
        inserted = conn.total_changes > before
        if not inserted:
            logger.info(
                "Duplicate event skipped",
                extra={"event_id": record["event_id"]},
            )
        return inserted
    except sqlite3.Error as exc:
        logger.error(
            "SQLite write error",
            extra={"error": str(exc), "event_id": record["event_id"]},
        )
        raise
