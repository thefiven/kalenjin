from __future__ import annotations

from datetime import datetime
from typing import Any

from kalenjin.sync.domain import ActivityRecord

_GARMIN_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def parse_activity(raw: dict[str, Any]) -> ActivityRecord:
    """Turn a raw Garmin Connect activity payload into an `ActivityRecord`.

    Keeps the full raw payload alongside the parsed fields so metrics we don't
    parse today can still be recovered later without re-fetching from Garmin.
    """
    activity_type = raw.get("activityType") or {}
    sport = activity_type.get("typeKey", "unknown")

    return ActivityRecord(
        garmin_activity_id=str(raw["activityId"]),
        sport=sport,
        started_at=datetime.strptime(raw["startTimeLocal"], _GARMIN_TIME_FORMAT),
        duration_seconds=float(raw["duration"]),
        distance_meters=_optional_float(raw.get("distance")),
        average_heart_rate=_optional_float(raw.get("averageHR")),
        raw_payload=raw,
    )


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)
