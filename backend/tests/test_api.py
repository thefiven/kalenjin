from datetime import date, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from kalenjin.api import (
    app,
    get_activity_repository,
    get_activity_source,
    get_garmin_push_client,
    get_llm_client,
    get_objectif_repository,
    get_plan_repository,
    get_rapport_repository,
)
from kalenjin.rapport.domain import RapportRecord
from kalenjin.sync.domain import ActivityRecord
from support.api_client import overriding_dependencies
from support.fakes import (
    FakeLLMClient,
    FakeObjectifRepository,
    FakePlanRepository,
    FakeRapportRepository,
    FakeRepository,
    FakeSource,
    RejectsPush,
    raw_activity,
)


class _AnyRangeSource(RejectsPush):
    """Returns the same activities regardless of the requested date range —
    the endpoint test only cares about the final imported count, not chunking.

    Every test using this fake exercises a route with no active plan/objectif, so
    push (via the inherited `RejectsPush`) is never expected to actually fire."""

    def __init__(self, raw_activities: list[dict[str, Any]]) -> None:
        self._raw_activities = raw_activities

    def fetch_activities(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        return self._raw_activities


def test_get_garmin_push_client_rejects_a_narrow_activity_only_source() -> None:
    """`get_activity_source` overridden with something only `ActivitySource`-shaped
    (no push_workout/delete_workout) must fail loudly right here, not with a
    confusing AttributeError buried inside a later Garmin push call."""
    with pytest.raises(AssertionError):
        get_garmin_push_client(source=FakeSource({}))


def test_health_check() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sync_endpoint_reports_the_number_of_imported_activities() -> None:
    source = _AnyRangeSource([raw_activity("1")])
    repo = FakeRepository()

    with overriding_dependencies(
        {
            get_activity_source: lambda: source,
            get_activity_repository: lambda: repo,
            get_objectif_repository: lambda: FakeObjectifRepository(),
            get_plan_repository: lambda: FakePlanRepository(),
            get_llm_client: lambda: FakeLLMClient(""),
        }
    ):
        response = TestClient(app).post("/sync")

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
    with overriding_dependencies({get_activity_repository: lambda: repo}):
        response = TestClient(app).get("/activities")

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
    with overriding_dependencies({get_activity_repository: lambda: repo}):
        response = TestClient(app).get("/activities", params={"since": "2024-06-01"})

    assert response.status_code == 200
    body = response.json()
    assert [a["garmin_activity_id"] for a in body] == ["2"]


def test_get_activity_by_id_returns_its_detail() -> None:
    repo = FakeRepository(existing=[_record("42", datetime(2024, 6, 1, 7, 0), sport="cycling")])
    with overriding_dependencies({get_activity_repository: lambda: repo}):
        response = TestClient(app).get("/activities/42")

    assert response.status_code == 200
    body = response.json()
    assert body["garmin_activity_id"] == "42"
    assert body["sport"] == "cycling"
    assert body["distance_meters"] == 5000.0


def test_get_activity_by_id_returns_404_when_missing() -> None:
    repo = FakeRepository()
    with overriding_dependencies({get_activity_repository: lambda: repo}):
        response = TestClient(app).get("/activities/does-not-exist")

    assert response.status_code == 404


def test_generate_rapport_creates_and_persists_a_rapport() -> None:
    activity_repo = FakeRepository(existing=[_record("1", datetime(2024, 6, 1, 7, 0))])
    rapport_repo = FakeRapportRepository()
    llm = FakeLLMClient(
        '{"strengths": "Good pace.", "improvements": "Add strides.", '
        '"completed_as_planned": true, "perceived_effort": "as_expected", "flag": "none"}'
    )

    with overriding_dependencies(
        {
            get_activity_repository: lambda: activity_repo,
            get_rapport_repository: lambda: rapport_repo,
            get_objectif_repository: lambda: FakeObjectifRepository(),
            get_plan_repository: lambda: FakePlanRepository(),
            get_activity_source: lambda: _AnyRangeSource([]),
            get_llm_client: lambda: llm,
        }
    ):
        response = TestClient(app).post("/activities/1/rapport")

    assert response.status_code == 200
    body = response.json()
    assert body["garmin_activity_id"] == "1"
    assert body["strengths"] == "Good pace."
    assert body["improvements"] == "Add strides."
    assert rapport_repo.get_for_activity("1") is not None


def test_generate_rapport_returns_404_when_activity_is_missing() -> None:
    activity_repo = FakeRepository()
    rapport_repo = FakeRapportRepository()
    llm = FakeLLMClient('{"strengths": "x", "improvements": "y"}')

    with overriding_dependencies(
        {
            get_activity_repository: lambda: activity_repo,
            get_rapport_repository: lambda: rapport_repo,
            get_objectif_repository: lambda: FakeObjectifRepository(),
            get_plan_repository: lambda: FakePlanRepository(),
            get_activity_source: lambda: _AnyRangeSource([]),
            get_llm_client: lambda: llm,
        }
    ):
        response = TestClient(app).post("/activities/does-not-exist/rapport")

    assert response.status_code == 404


def test_get_rapport_returns_the_persisted_rapport() -> None:
    rapport_repo = FakeRapportRepository(
        existing=[
            RapportRecord(
                garmin_activity_id="1",
                strengths="Good pace.",
                improvements="Add strides.",
                generated_at=datetime(2024, 6, 1, 8, 0),
                completed_as_planned=True,
                perceived_effort="as_expected",
                flag="none",
            )
        ]
    )

    with overriding_dependencies({get_rapport_repository: lambda: rapport_repo}):
        response = TestClient(app).get("/activities/1/rapport")

    assert response.status_code == 200
    body = response.json()
    assert body["strengths"] == "Good pace."
    assert body["improvements"] == "Add strides."


def test_get_rapport_returns_404_when_missing() -> None:
    rapport_repo = FakeRapportRepository()

    with overriding_dependencies({get_rapport_repository: lambda: rapport_repo}):
        response = TestClient(app).get("/activities/does-not-exist/rapport")

    assert response.status_code == 404
