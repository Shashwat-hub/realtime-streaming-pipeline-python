"""Centralised configuration loaded from environment variables."""

import os

# ── Redis ─────────────────────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
STREAM_KEY = os.getenv("STREAM_KEY", "telemetry_stream")
CONSUMER_GROUP = os.getenv("CONSUMER_GROUP", "pipeline_group")
CONSUMER_NAME = os.getenv("CONSUMER_NAME", "consumer_1")

# ── Pipeline tuning ──────────────────────────────────────────────────
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))
SLEEP_INTERVAL = float(os.getenv("SLEEP_INTERVAL", "1.0"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RUN_DURATION_SECONDS = int(os.getenv("RUN_DURATION_SECONDS", "30"))

# ── KPI thresholds (value > threshold → is_degraded = True) ─────────
KPI_THRESHOLDS: dict[str, float] = {
    "temperature": float(os.getenv("THRESHOLD_TEMPERATURE", "80.0")),
    "humidity": float(os.getenv("THRESHOLD_HUMIDITY", "70.0")),
    "pressure": float(os.getenv("THRESHOLD_PRESSURE", "1050.0")),
    "vibration": float(os.getenv("THRESHOLD_VIBRATION", "5.0")),
}

# ── Paths ─────────────────────────────────────────────────────────────
DATA_DIR = os.getenv("DATA_DIR", "./data")
DB_PATH = os.path.join(DATA_DIR, "telemetry.db")
DLQ_PATH = os.path.join(DATA_DIR, "dlq.jsonl")
