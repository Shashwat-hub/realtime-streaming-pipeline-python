"""Event validation – schema checks + business-rule checks."""

from src.models import TelemetryEvent, REQUIRED_FIELDS, VALID_KPIS, VALID_ZONES


def validate_event(data: dict) -> TelemetryEvent:
    """Validate raw dict → TelemetryEvent.  Raises ValueError on any issue."""

    # 1. Required-field check
    missing = REQUIRED_FIELDS - set(data.keys())
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    # 2. Type coercion (will raise on non-numeric value, etc.)
    try:
        event = TelemetryEvent.from_dict(data)
    except (TypeError, ValueError, KeyError) as exc:
        raise ValueError(f"Invalid field types: {exc}") from exc

    # 3. KPI must be a known metric
    if event.kpi not in VALID_KPIS:
        raise ValueError(
            f"Unknown kpi '{event.kpi}'. Valid: {sorted(VALID_KPIS)}"
        )

    # 4. Zone must be recognised
    if event.zone not in VALID_ZONES:
        raise ValueError(
            f"Unknown zone '{event.zone}'. Valid: {sorted(VALID_ZONES)}"
        )

    # 5. Value must be non-negative
    if event.value < 0:
        raise ValueError(f"Value must be non-negative, got {event.value}")

    return event
