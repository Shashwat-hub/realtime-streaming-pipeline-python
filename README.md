# realtime-streaming-pipeline-python

A minimal, production-style **real-time data pipeline** built with Python, Redis Streams, and SQLite.  
Designed to demonstrate reliability patterns (idempotency, retries, DLQ, structured logging) in a clean, modular codebase that runs locally with `docker-compose`.

---

## Architecture

```
┌────────────┐      ┌───────────────┐      ┌────────────────────────────────────────┐
│  Producer   │─────▶│  Redis Stream  │─────▶│              Consumer                  │
│ (telemetry  │ XADD │ (telemetry_   │XREAD-│                                        │
│  generator) │      │  stream)       │GROUP │  ┌───────────┐  ┌───────────┐  ┌─────┐ │
└────────────┘      └───────────────┘      │  │ Validator  │─▶│ Processor │─▶│Sink │ │
                                            │  └─────┬─────┘  └───────────┘  │(SQL)│ │
                                            │        │ fail                   └──┬──┘ │
                                            │        ▼                           │    │
                                            │  ┌───────────┐          ┌─────────┐│    │
                                            │  │  Retries   │          │telemetry││    │
                                            │  └─────┬─────┘          │  .db    ││    │
                                            │        │ exhausted      └─────────┘│    │
                                            │        ▼                           │    │
                                            │  ┌───────────┐                     │    │
                                            │  │    DLQ     │                     │    │
                                            │  │(dlq.jsonl) │                     │    │
                                            │  └───────────┘                     │    │
                                            └────────────────────────────────────┘
```

### Data flow

1. **Producer** generates realistic telemetry events (`event_id`, `device_id`, `zone`, `ts`, `kpi`, `value`) and publishes them to a **Redis Stream** via `XADD`.
2. **Consumer** reads batches via a **consumer group** (`XREADGROUP`), ensuring at-least-once delivery.
3. Each event passes through:
   - **Validator** – schema & business-rule checks.
   - **Processor** – derives `is_degraded` by comparing `value` against configurable KPI thresholds.
   - **Sink** – writes to SQLite with `INSERT OR IGNORE` on `event_id` PK for **idempotency**.
4. Events that fail validation are routed directly to the **DLQ**.  Transient errors are retried up to `MAX_RETRIES` times with linear back-off before landing in the DLQ.

---

## Repository tree

```
realtime-streaming-pipeline-python/
├── docker-compose.yml
├── Dockerfile
├── .dockerignore
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.txt
├── README.md
├── src/
│   ├── __init__.py
│   ├── config.py          # env-var configuration
│   ├── models.py           # TelemetryEvent dataclass
│   ├── logger.py           # structured JSON logger
│   ├── redis_client.py     # Redis stream helpers
│   ├── producer.py         # telemetry event generator
│   ├── consumer.py         # pipeline orchestrator
│   ├── validator.py        # event validation
│   ├── processor.py        # KPI threshold processing
│   ├── sink.py             # SQLite writer (idempotent)
│   └── dlq.py              # dead-letter queue (file)
└── tests/
    ├── __init__.py
    ├── test_validator.py    # validation unit tests
    └── test_dedupe.py       # idempotency unit tests
```

---

## Quick start

### Prerequisites

- **Docker** & **Docker Compose** (v2)

### Run

```bash
# Clone and enter the project
git clone <repo-url> && cd realtime-streaming-pipeline-python

# (Optional) customise configuration
cp .env.example .env   # edit .env as needed

# Build & run
docker-compose up --build
```

The producer runs for **30 s** (default) and the consumer for **35 s**, then both exit cleanly.

### Run tests (no Docker needed)

```bash
pip install -r requirements.txt
pytest -v
```

---

## Configuration

All settings are controlled via environment variables (set in `docker-compose.yml` or a `.env` file):

| Variable | Default | Description |
|---|---|---|
| `BATCH_SIZE` | `5` (producer) / `10` (consumer) | Events per batch |
| `SLEEP_INTERVAL` | `1.0` / `0.5` | Seconds between batches |
| `PRODUCER_RUN_DURATION` | `30` | Producer lifetime (seconds) |
| `CONSUMER_RUN_DURATION` | `35` | Consumer lifetime (seconds) |
| `MAX_RETRIES` | `3` | Retry attempts before DLQ |
| `THRESHOLD_TEMPERATURE` | `80.0` | Degradation threshold |
| `THRESHOLD_HUMIDITY` | `70.0` | Degradation threshold |
| `THRESHOLD_PRESSURE` | `1050.0` | Degradation threshold |
| `THRESHOLD_VIBRATION` | `5.0` | Degradation threshold |
| `REDIS_HOST` | `redis` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |
| `DATA_DIR` | `/data` (docker) / `./data` (local) | Directory for SQLite DB and DLQ storage |

---

## Sample output

### Producer log (JSON)

```json
{"asctime": "2025-01-15T10:00:01", "name": "producer", "levelname": "INFO", "message": "Event published", "event_id": "a1b2c3d4-...", "kpi": "temperature", "value": "82.35"}
```

### Consumer log (JSON)

```json
{"asctime": "2025-01-15T10:00:02", "name": "consumer", "levelname": "INFO", "message": "Event processed", "event_id": "a1b2c3d4-...", "is_degraded": true, "attempt": 1}
```

### DLQ entry (`data/dlq.jsonl`)

```json
{"event": {"event_id": "...", "value": "-1.0", ...}, "error": "Value must be non-negative, got -1.0", "failed_at": 1705312803.45}
```

---

## Inspecting results

### SQLite

```bash
# From the host (after docker-compose down):
# Option 1 — use docker volume
docker run --rm -v realtime-streaming-pipeline-python_pipeline-data:/data alpine \
  sh -c "apk add sqlite && sqlite3 /data/telemetry.db 'SELECT * FROM telemetry_events LIMIT 10;'"

# Option 2 — exec into consumer container while it's running
docker-compose exec consumer python -c "
import sqlite3, json
conn = sqlite3.connect('/data/telemetry.db')
conn.row_factory = sqlite3.Row
rows = conn.execute('SELECT * FROM telemetry_events LIMIT 5').fetchall()
for r in rows:
    print(json.dumps(dict(r), indent=2))
"
```

### DLQ

```bash
docker run --rm -v realtime-streaming-pipeline-python_pipeline-data:/data alpine \
  cat /data/dlq.jsonl
```

### Row counts

```bash
docker-compose exec consumer python -c "
import sqlite3
conn = sqlite3.connect('/data/telemetry.db')
total = conn.execute('SELECT COUNT(*) FROM telemetry_events').fetchone()[0]
degraded = conn.execute('SELECT COUNT(*) FROM telemetry_events WHERE is_degraded = 1').fetchone()[0]
print(f'Total events: {total}')
print(f'Degraded:     {degraded}')
print(f'Healthy:      {total - degraded}')
"
```

---

## Reliability patterns

| Pattern | Implementation |
|---|---|
| **Idempotency** | `INSERT OR IGNORE` on `event_id` PK – reprocessing is a safe no-op |
| **Retries** | Configurable `MAX_RETRIES` with linear back-off (`0.5s × attempt`) |
| **Dead-letter queue** | Failed events (after retries) appended to `dlq.jsonl` with error + timestamp |
| **Structured logging** | JSON-line logs via `python-json-logger` for easy parsing |
| **At-least-once delivery** | Redis consumer groups (`XREADGROUP` + `XACK`) |

---

## Scalability Considerations

- Stateless producer and consumer enable horizontal scaling via multiple consumer replicas.
- Redis consumer groups allow parallel message processing across multiple workers.
- Current primary bottleneck is the SQLite sink (single-writer), which can be replaced with Postgres or a distributed store for higher throughput.
- Stream partitioning (e.g., by zone or device_id) can be introduced for parallel log scaling similar to Kafka partitions.
- Architecture is broker-agnostic and can migrate to Kafka/Kinesis without changing core processing logic.
- This implementation prioritizes correctness and reliability semantics before infrastructure scaling.


## License

MIT
