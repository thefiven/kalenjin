from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class DateRange:
    since: date | None = None
    until: date | None = None


@dataclass(frozen=True)
class ActivityRecord:
    """A parsed Garmin activity, ready to persist. See CONTEXT.md's `Séance` term."""

    garmin_activity_id: str
    sport: str
    started_at: datetime
    duration_seconds: float
    distance_meters: float | None
    average_heart_rate: float | None
    raw_payload: dict[str, Any]


class ActivitySource(Protocol):
    """Anything that can supply raw Garmin activity payloads for a date range."""

    def fetch_activities(self, start_date: date, end_date: date) -> list[dict[str, Any]]: ...


class ActivityRepository(Protocol):
    """Persistence boundary for activities, independent of any specific database."""

    def has_any(self) -> bool: ...

    def latest_started_at(self) -> datetime | None: ...

    def upsert_many(self, activities: list[ActivityRecord]) -> int:
        """Persist activities, ignoring ones that already exist (by garmin_activity_id).

        Returns the number of newly-inserted activities.
        """
        ...

    def list_activities(self, date_range: DateRange = DateRange()) -> list[ActivityRecord]:
        """All activities whose start date falls within date_range, most recent first."""
        ...

    def get_activity(self, garmin_activity_id: str) -> ActivityRecord | None: ...
