from datetime import date, datetime
from typing import Any

from kalenjin.sync.domain import ActivityRecord
from kalenjin.sync.service import HISTORICAL_IMPORT_START, sync_activities


class FakeSource:
    def __init__(self, activities_by_range: dict[tuple[date, date], list[dict[str, Any]]]) -> None:
        self._activities_by_range = activities_by_range
        self.calls: list[tuple[date, date]] = []

    def fetch_activities(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        self.calls.append((start_date, end_date))
        return self._activities_by_range.get((start_date, end_date), [])


class FakeRepository:
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


def _raw(activity_id: str, started_at: str = "2024-06-01 07:30:00") -> dict[str, Any]:
    return {
        "activityId": activity_id,
        "activityType": {"typeKey": "running"},
        "startTimeLocal": started_at,
        "duration": 1800.0,
        "distance": 5000.0,
        "averageHR": 150,
    }


def test_empty_repository_triggers_full_historical_import() -> None:
    today = date(2024, 6, 10)
    source = FakeSource({(HISTORICAL_IMPORT_START, today): [_raw("1")]})
    repo = FakeRepository()

    result = sync_activities(source, repo, today=today)

    assert source.calls == [(HISTORICAL_IMPORT_START, today)]
    assert result.imported_count == 1


def test_non_empty_repository_syncs_incrementally_from_latest_activity() -> None:
    today = date(2024, 6, 10)
    last_synced = datetime(2024, 6, 5, 8, 0, 0)
    existing = ActivityRecord(
        garmin_activity_id="1",
        sport="running",
        started_at=last_synced,
        duration_seconds=1800,
        distance_meters=5000,
        average_heart_rate=150,
        raw_payload={},
    )
    source = FakeSource({(last_synced.date(), today): [_raw("2", "2024-06-06 07:00:00")]})
    repo = FakeRepository(existing=[existing])

    result = sync_activities(source, repo, today=today)

    assert source.calls == [(last_synced.date(), today)]
    assert result.imported_count == 1


def test_reimporting_the_same_activity_is_not_counted_as_new() -> None:
    today = date(2024, 6, 10)
    source = FakeSource({(HISTORICAL_IMPORT_START, today): [_raw("1")]})
    repo = FakeRepository()

    sync_activities(source, repo, today=today)
    second_result = sync_activities(source, repo, today=today)

    assert second_result.imported_count == 0


def test_no_activities_returned_yields_zero_imported() -> None:
    today = date(2024, 6, 10)
    source = FakeSource({})
    repo = FakeRepository()

    result = sync_activities(source, repo, today=today)

    assert result.imported_count == 0
