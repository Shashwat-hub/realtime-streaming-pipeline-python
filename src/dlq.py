"""Dead-letter queue – appends failed events as JSON-lines to a file."""

import json
import os
import time

from src.config import DLQ_PATH
from src.logger import get_logger

logger = get_logger("dlq")


def send_to_dlq(
    event_data: dict,
    error_message: str,
    dlq_path: str | None = None,
) -> None:
    """Persist a failed event with its error context to the DLQ file."""
    path = dlq_path or DLQ_PATH
    if os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)

    record = {
        "event": event_data,
        "error": error_message,
        "failed_at": time.time(),
    }
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")

    logger.warning(
        "Event sent to DLQ",
        extra={
            "event_id": event_data.get("event_id"),
            "error": error_message,
        },
    )
