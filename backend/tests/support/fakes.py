from datetime import date, datetime
from typing import Any

from kalenjin.sync.domain import ActivityRecord


class FakeSource:
    """In-memory `sync.domain.ActivitySource` — no real Garmin call."""

    def __init__(self, activities_by_range: dict[tuple[date, date], list[dict[str, Any]]]) -> None:
        self._activities_by_range = activities_by_range
        self.calls: list[tuple[date, date]] = []

    def fetch_activities(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        self.calls.append((start_date, end_date))
        return self._activities_by_range.get((start_date, end_date), [])


class FakeRepository:
    """In-memory `sync.domain.ActivityRepository` — no real database."""

    def __init__(self, existing: list[ActivityRecord] | None = None) -> None:
        self._existing = {a.garmin_activity_id: a for a in (existing or [])}
        self.upsert_calls: list[list[ActivityRecord]] = []

    def has_any(self) -> bool:
        return bool(self._existing)

    def latest_started_at(self) -> datetime | None:
        if not self._existing:
            return None
        return max(a.started_at for a in self._existing.values())

    def upsert_many(self, activities: list[ActivityRecord]) -> int:
        self.upsert_calls.append(activities)
        inserted = 0
        for activity in activities:
            if activity.garmin_activity_id not in self._existing:
                inserted += 1
            self._existing[activity.garmin_activity_id] = activity
        return inserted

    def list_activities(
        self, since: date | None = None, until: date | None = None
    ) -> list[ActivityRecord]:
        activities = self._existing.values()
        if since is not None:
            activities = (a for a in activities if a.started_at.date() >= since)
        if until is not None:
            activities = (a for a in activities if a.started_at.date() <= until)
        return sorted(activities, key=lambda a: a.started_at, reverse=True)

    def get_activity(self, garmin_activity_id: str) -> ActivityRecord | None:
        return self._existing.get(garmin_activity_id)


def raw_activity(activity_id: str, started_at: str = "2024-06-01 07:30:00") -> dict[str, Any]:
    return {
        "activityId": activity_id,
        "activityType": {"typeKey": "running"},
        "startTimeLocal": started_at,
        "duration": 1800.0,
        "distance": 5000.0,
        "averageHR": 150,
    }
