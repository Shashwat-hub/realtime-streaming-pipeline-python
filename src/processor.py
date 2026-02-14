"""Event processor – derives is_degraded from KPI thresholds."""

from src.config import KPI_THRESHOLDS
from src.models import TelemetryEvent


def process_event(event: TelemetryEvent) -> dict:
    """Enrich the event with an ``is_degraded`` flag.

    Returns a plain dict ready for the sink.
    """
    threshold = KPI_THRESHOLDS.get(event.kpi)
    is_degraded = event.value > threshold if threshold is not None else False

    record = event.to_dict()
    record["is_degraded"] = is_degraded
    return record
