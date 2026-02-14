"""Producer – generates realistic telemetry events and publishes to Redis."""

import random
import time
import uuid

from src.config import BATCH_SIZE, SLEEP_INTERVAL, RUN_DURATION_SECONDS
from src.logger import get_logger
from src.models import VALID_KPIS, VALID_ZONES
from src.redis_client import get_redis_client, publish_event

logger = get_logger("producer")

# Realistic value ranges per KPI
KPI_RANGES: dict[str, tuple[float, float]] = {
    "temperature": (15.0, 100.0),
    "humidity": (10.0, 95.0),
    "pressure": (950.0, 1100.0),
    "vibration": (0.0, 10.0),
}

DEVICE_IDS = [f"device-{i:03d}" for i in range(1, 21)]


def generate_event() -> dict:
    """Build a single telemetry event dict (all string values for Redis)."""
    kpi = random.choice(sorted(VALID_KPIS))
    low, high = KPI_RANGES[kpi]

    event = {
        "event_id": str(uuid.uuid4()),
        "device_id": random.choice(DEVICE_IDS),
        "zone": random.choice(sorted(VALID_ZONES)),
        "ts": str(time.time()),
        "kpi": kpi,
        "value": str(round(random.uniform(low, high), 2)),
    }

    # ~5 % chance of a bad event (negative value) to exercise the DLQ path
    if random.random() < 0.05:
        event["value"] = str(-1.0)

    return event


def run_producer() -> None:
    """Main producer loop – runs for RUN_DURATION_SECONDS then exits."""
    logger.info(
        "Producer starting",
        extra={
            "batch_size": BATCH_SIZE,
            "sleep_interval": SLEEP_INTERVAL,
            "run_duration": RUN_DURATION_SECONDS,
        },
    )

    client = get_redis_client()
    start = time.time()
    total_published = 0

    while time.time() - start < RUN_DURATION_SECONDS:
        for _ in range(BATCH_SIZE):
            event = generate_event()
            msg_id = publish_event(client, event)
            total_published += 1
            logger.info(
                "Event published",
                extra={
                    "event_id": event["event_id"],
                    "stream_id": msg_id,
                    "kpi": event["kpi"],
                    "value": event["value"],
                },
            )
        time.sleep(SLEEP_INTERVAL)

    logger.info("Producer finished", extra={"total_published": total_published})


if __name__ == "__main__":
    run_producer()
