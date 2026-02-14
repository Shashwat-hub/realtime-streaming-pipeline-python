"""Tests for src.validator.validate_event."""

import pytest

from src.validator import validate_event


def _make_event(**overrides) -> dict:
    """Return a valid event dict, with optional field overrides."""
    base = {
        "event_id": "evt-001",
        "device_id": "device-001",
        "zone": "zone-a",
        "ts": "1700000000.0",
        "kpi": "temperature",
        "value": "72.5",
    }
    base.update(overrides)
    return base


class TestValidateEvent:
    """Validator should accept good data and reject bad data."""

    def test_valid_event_passes(self):
        event = validate_event(_make_event())
        assert event.event_id == "evt-001"
        assert event.kpi == "temperature"
        assert event.value == 72.5

    def test_missing_field_raises(self):
        bad = _make_event()
        del bad["kpi"]
        with pytest.raises(ValueError, match="Missing required fields"):
            validate_event(bad)

    def test_unknown_kpi_raises(self):
        with pytest.raises(ValueError, match="Unknown kpi"):
            validate_event(_make_event(kpi="unknown_metric"))

    def test_unknown_zone_raises(self):
        with pytest.raises(ValueError, match="Unknown zone"):
            validate_event(_make_event(zone="zone-x"))

    def test_negative_value_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            validate_event(_make_event(value="-5.0"))

    def test_non_numeric_value_raises(self):
        with pytest.raises(ValueError, match="Invalid field types"):
            validate_event(_make_event(value="not_a_number"))
