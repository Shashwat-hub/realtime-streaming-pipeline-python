"""Consumer – reads from Redis stream, validates, processes, sinks to SQLite."""

import time

from src.config import (
    BATCH_SIZE,
    CONSUMER_NAME,
    MAX_RETRIES,
    RUN_DURATION_SECONDS,
)
from src.dlq import send_to_dlq
from src.logger import get_logger
from src.processor import process_event
from src.redis_client import (
    ack_event,
    ensure_consumer_group,
    get_redis_client,
    read_events,
)
from src.sink import init_db, write_event
from src.validator import validate_event

logger = get_logger("consumer")


def handle_message(conn, data: dict, message_id: str, client) -> None:
    """Validate → process → sink a single message with retry + DLQ."""
    last_error: str | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            event = validate_event(data)
            record = process_event(event)
            write_event(conn, record)
            ack_event(client, message_id)
            logger.info(
                "Event processed",
                extra={
                    "event_id": data.get("event_id"),
                    "is_degraded": record["is_degraded"],
                    "attempt": attempt,
                },
            )
            return
        except ValueError as exc:
            # Validation errors are deterministic → skip retries
            last_error = str(exc)
            logger.warning(
                "Validation failed – routing to DLQ",
                extra={"event_id": data.get("event_id"), "error": last_error},
            )
            break
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            logger.warning(
                "Processing attempt failed",
                extra={
                    "event_id": data.get("event_id"),
                    "attempt": attempt,
                    "max_retries": MAX_RETRIES,
                    "error": last_error,
                },
            )
            if attempt < MAX_RETRIES:
                time.sleep(0.5 * attempt)  # linear back-off

    # All retries exhausted or non-retryable validation error
    send_to_dlq(data, last_error or "unknown error")
    ack_event(client, message_id)


def run_consumer() -> None:
    """Main consumer loop – runs for RUN_DURATION_SECONDS then exits."""
    logger.info(
        "Consumer starting",
        extra={
            "batch_size": BATCH_SIZE,
            "max_retries": MAX_RETRIES,
            "run_duration": RUN_DURATION_SECONDS,
        },
    )

    client = get_redis_client()
    ensure_consumer_group(client)
    conn = init_db()

    start = time.time()
    total_processed = 0

    while time.time() - start < RUN_DURATION_SECONDS:
        results = read_events(client, CONSUMER_NAME, count=BATCH_SIZE, block_ms=2000)
        if not results:
            continue
        for _stream_name, messages in results:
            for message_id, data in messages:
                handle_message(conn, data, message_id, client)
                total_processed += 1

    conn.close()
    logger.info("Consumer finished", extra={"total_processed": total_processed})


if __name__ == "__main__":
    run_consumer()
