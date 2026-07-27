from collections.abc import Iterator
from datetime import date, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from kalenjin.api import (
    _get_db_session,
    app,
    get_current_user,
    get_engine,
    get_garmin_connection,
    get_gemini_connection,
    get_user_scope,
)
from kalenjin.auth.domain import UserRecord
from kalenjin.rapport.domain import RapportRecord
from kalenjin.sync.domain import ActivityRecord
from support.api_client import overriding_dependencies
from support.fakes import (
    FakeGarminConnection,
    FakeGeminiConnection,
    FakeLLMClient,
    FakeRapportRepository,
    FakeRepository,
    RejectsPush,
    fake_user_scope,
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


def test_health_check() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_engine_is_cached_for_the_same_database_url() -> None:
    """`_get_db_session` runs once per HTTP request, not once per process — without
    caching, every request would open a fresh connection pool and abandon it at
    request end. `get_engine` is cached by `database_url` (a plain, hashable string,
    unlike `DbConfig` itself) so the process holds exactly one `Engine`/pool for its
    lifetime."""
    first = get_engine("postgresql+psycopg://cache-test-a")
    second = get_engine("postgresql+psycopg://cache-test-a")

    assert first is second


def test_get_engine_returns_a_distinct_engine_per_database_url() -> None:
    first = get_engine("postgresql+psycopg://cache-test-b")
    second = get_engine("postgresql+psycopg://cache-test-c")

    assert first is not second


@pytest.mark.integration
def test_a_freshly_signed_up_user_sees_a_clean_empty_state_everywhere(
    db_session: Session, user_id: int
) -> None:
    """Issue #31, acceptance criterion 1: since no pre-existing owner data was ever
    migrated (ADR-0011 — none existed to migrate), the owner's first post-launch login
    must land on a clean empty state, exactly like any other brand-new user.

    Exercises the real, session-backed per-user repositories (only
    `_get_db_session`/`get_current_user` are faked) rather than empty-by-construction
    fakes — see `test_multi_tenant_isolation.py`'s module docstring for why that
    distinction matters: a fake that's empty for everyone proves nothing about this
    specific user's real, `user_id`-scoped rows being empty."""

    def _session_override() -> Iterator[Session]:
        yield db_session

    fake_user = UserRecord(
        id=user_id, google_subject="fresh-subject", email="fresh@x.com", created_at=datetime.now()
    )

    with overriding_dependencies(
        {_get_db_session: _session_override, get_current_user: lambda: fake_user}
    ):
        client = TestClient(app)
        assert client.get("/activities").json() == []
        assert client.get("/objectif").status_code == 404
        assert client.get("/plan").status_code == 404


def test_sync_endpoint_reports_the_number_of_imported_activities() -> None:
    source = _AnyRangeSource([raw_activity("1")])
    repo = FakeRepository()

    with overriding_dependencies(
        {
            get_garmin_connection: lambda: FakeGarminConnection(session=source),
            get_user_scope: lambda: fake_user_scope(activities=repo),
            get_gemini_connection: lambda: FakeGeminiConnection(client=FakeLLMClient("")),
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
    with overriding_dependencies({get_user_scope: lambda: fake_user_scope(activities=repo)}):
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
    with overriding_dependencies({get_user_scope: lambda: fake_user_scope(activities=repo)}):
        response = TestClient(app).get("/activities", params={"since": "2024-06-01"})

    assert response.status_code == 200
    body = response.json()
    assert [a["garmin_activity_id"] for a in body] == ["2"]


def test_get_activity_by_id_returns_its_detail() -> None:
    repo = FakeRepository(existing=[_record("42", datetime(2024, 6, 1, 7, 0), sport="cycling")])
    with overriding_dependencies({get_user_scope: lambda: fake_user_scope(activities=repo)}):
        response = TestClient(app).get("/activities/42")

    assert response.status_code == 200
    body = response.json()
    assert body["garmin_activity_id"] == "42"
    assert body["sport"] == "cycling"
    assert body["distance_meters"] == 5000.0


def test_get_activity_by_id_returns_404_when_missing() -> None:
    repo = FakeRepository()
    with overriding_dependencies({get_user_scope: lambda: fake_user_scope(activities=repo)}):
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
            get_user_scope: lambda: fake_user_scope(
                activities=activity_repo, rapports=rapport_repo
            ),
            get_garmin_connection: lambda: FakeGarminConnection(session=_AnyRangeSource([])),
            get_gemini_connection: lambda: FakeGeminiConnection(client=llm),
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
            get_user_scope: lambda: fake_user_scope(
                activities=activity_repo, rapports=rapport_repo
            ),
            get_garmin_connection: lambda: FakeGarminConnection(session=_AnyRangeSource([])),
            get_gemini_connection: lambda: FakeGeminiConnection(client=llm),
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

    with overriding_dependencies({get_user_scope: lambda: fake_user_scope(rapports=rapport_repo)}):
        response = TestClient(app).get("/activities/1/rapport")

    assert response.status_code == 200
    body = response.json()
    assert body["strengths"] == "Good pace."
    assert body["improvements"] == "Add strides."


def test_get_rapport_returns_404_when_missing() -> None:
    rapport_repo = FakeRapportRepository()

    with overriding_dependencies({get_user_scope: lambda: fake_user_scope(rapports=rapport_repo)}):
        response = TestClient(app).get("/activities/does-not-exist/rapport")

    assert response.status_code == 404
