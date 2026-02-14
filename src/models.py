"""Telemetry event data model and constants."""

from dataclasses import dataclass, asdict
import json


REQUIRED_FIELDS = {"event_id", "device_id", "zone", "ts", "kpi", "value"}
VALID_KPIS = {"temperature", "humidity", "pressure", "vibration"}
VALID_ZONES = {"zone-a", "zone-b", "zone-c", "zone-d"}


@dataclass(frozen=True)
class TelemetryEvent:
    """Immutable representation of a single telemetry reading."""

    event_id: str
    device_id: str
    zone: str
    ts: float
    kpi: str
    value: float

    # ── serialisation helpers ─────────────────────────────────────────

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "TelemetryEvent":
        return cls(
            event_id=str(data["event_id"]),
            device_id=str(data["device_id"]),
            zone=str(data["zone"]),
            ts=float(data["ts"]),
            kpi=str(data["kpi"]),
            value=float(data["value"]),
        )
