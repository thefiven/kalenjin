from datetime import date, datetime
from typing import Any

from fastapi.testclient import TestClient

from kalenjin.api import app, get_activity_repository, get_activity_source
from kalenjin.sync.domain import ActivityRecord
from support.fakes import FakeRepository, raw_activity


class _AnyRangeSource:
    """Returns the same activities regardless of the requested date range —
    the endpoint test only cares about the final imported count, not chunking."""

    def __init__(self, raw_activities: list[dict[str, Any]]) -> None:
        self._raw_activities = raw_activities

    def fetch_activities(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        return self._raw_activities


def test_health_check() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sync_endpoint_reports_the_number_of_imported_activities() -> None:
    source = _AnyRangeSource([raw_activity("1")])
    repo = FakeRepository()

    app.dependency_overrides[get_activity_source] = lambda: source
    app.dependency_overrides[get_activity_repository] = lambda: repo
    try:
        client = TestClient(app)
        response = client.post("/sync")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"imported_count": 1}


def _record(activity_id: str, started_at: datetime, sport: str = "running") -> ActivityRecord:
    return ActivityRecord(
        garmin_activity_id=activity_id,
        sport=sport,
        started_at=started_at,
        duration_seconds=1800.0,
        distance_meters=5000.0,
        average_heart_rate=150.0,
        raw_payload={},
    )


def test_list_activities_returns_activities_most_recent_first() -> None:
    repo = FakeRepository(
        existing=[
            _record("1", datetime(2024, 6, 1, 7, 0)),
            _record("2", datetime(2024, 6, 5, 7, 0)),
        ]
    )
    app.dependency_overrides[get_activity_repository] = lambda: repo
    try:
        client = TestClient(app)
        response = client.get("/activities")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert [a["garmin_activity_id"] for a in body] == ["2", "1"]


def test_list_activities_filters_by_date_range() -> None:
    repo = FakeRepository(
        existing=[
            _record("1", datetime(2024, 5, 1, 7, 0)),
            _record("2", datetime(2024, 6, 5, 7, 0)),
        ]
    )
    app.dependency_overrides[get_activity_repository] = lambda: repo
    try:
        client = TestClient(app)
        response = client.get("/activities", params={"since": "2024-06-01"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert [a["garmin_activity_id"] for a in body] == ["2"]


def test_get_activity_by_id_returns_its_detail() -> None:
    repo = FakeRepository(existing=[_record("42", datetime(2024, 6, 1, 7, 0), sport="cycling")])
    app.dependency_overrides[get_activity_repository] = lambda: repo
    try:
        client = TestClient(app)
        response = client.get("/activities/42")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["garmin_activity_id"] == "42"
    assert body["sport"] == "cycling"
    assert body["distance_meters"] == 5000.0


def test_get_activity_by_id_returns_404_when_missing() -> None:
    repo = FakeRepository()
    app.dependency_overrides[get_activity_repository] = lambda: repo
    try:
        client = TestClient(app)
        response = client.get("/activities/does-not-exist")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
