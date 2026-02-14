"""Redis connection and stream helpers (XADD / XREADGROUP / XACK)."""

import redis

from src.config import REDIS_HOST, REDIS_PORT, STREAM_KEY, CONSUMER_GROUP


def get_redis_client() -> redis.Redis:
    """Return a connected Redis client with string decoding enabled."""
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def ensure_consumer_group(client: redis.Redis) -> None:
    """Create the consumer group idempotently (ignores BUSYGROUP error)."""
    try:
        client.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


def publish_event(client: redis.Redis, event_data: dict) -> str:
    """Append an event to the Redis stream. Returns the stream message ID."""
    return client.xadd(STREAM_KEY, event_data)


def read_events(
    client: redis.Redis,
    consumer_name: str,
    count: int = 10,
    block_ms: int = 2000,
):
    """Read new messages from the stream via the consumer group."""
    return client.xreadgroup(
        CONSUMER_GROUP,
        consumer_name,
        {STREAM_KEY: ">"},
        count=count,
        block=block_ms,
    )


def ack_event(client: redis.Redis, message_id: str) -> None:
    """Acknowledge a successfully processed message."""
    client.xack(STREAM_KEY, CONSUMER_GROUP, message_id)
