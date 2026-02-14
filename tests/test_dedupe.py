"""Tests for idempotent writes (dedupe by event_id) in src.sink."""

from src.sink import init_db, write_event


def _make_record(**overrides) -> dict:
    """Return a processed record dict ready for the sink."""
    base = {
        "event_id": "evt-dedupe-001",
        "device_id": "device-010",
        "zone": "zone-b",
        "ts": 1700000000.0,
        "kpi": "humidity",
        "value": 65.0,
        "is_degraded": False,
    }
    base.update(overrides)
    return base


class TestIdempotentWrites:
    """INSERT OR IGNORE on the event_id PK must prevent duplicates."""

    def test_first_insert_succeeds(self):
        conn = init_db(":memory:")
        result = write_event(conn, _make_record())
        assert result is True

        count = conn.execute("SELECT COUNT(*) FROM telemetry_events").fetchone()[0]
        assert count == 1
        conn.close()

    def test_duplicate_insert_is_ignored(self):
        conn = init_db(":memory:")
        write_event(conn, _make_record())
        result = write_event(conn, _make_record())  # same event_id
        assert result is False

        count = conn.execute("SELECT COUNT(*) FROM telemetry_events").fetchone()[0]
        assert count == 1  # still only one row
        conn.close()

    def test_different_event_ids_both_inserted(self):
        conn = init_db(":memory:")
        write_event(conn, _make_record(event_id="aaa"))
        write_event(conn, _make_record(event_id="bbb"))

        count = conn.execute("SELECT COUNT(*) FROM telemetry_events").fetchone()[0]
        assert count == 2
        conn.close()
