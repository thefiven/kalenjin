"""Issue #28: two logged-in users must never see each other's data through the
existing endpoints. Only `_get_db_session` and `get_current_user` are overridden here
— every repository runs as its real, session-backed implementation, since the whole
point is to exercise the real per-user SQL filtering, not a fake that never scoped
anything to begin with."""

import json
from collections.abc import Iterator
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from kalenjin.api import (
    _get_db_session,
    app,
    get_current_user,
    get_garmin_connection,
    get_gemini_connection,
)
from kalenjin.auth.domain import UserRecord
from support.api_client import overriding_dependencies
from support.fakes import (
    FakeGarminConnection,
    FakeGeminiConnection,
    FakeLLMClient,
    FakeSource,
    RejectsPush,
    raw_activity,
)

pytestmark = pytest.mark.integration


def _rapport_llm_response() -> str:
    return json.dumps(
        {
            "strengths": "Good pace.",
            "improvements": "Add strides.",
            "completed_as_planned": True,
            "perceived_effort": "as_expected",
            "flag": "none",
        }
    )


class _SyncSource(RejectsPush):
    def __init__(self, activities: list[dict[str, object]]) -> None:
        self._activities = activities

    def fetch_activities(self, start_date: date, end_date: date) -> list[dict[str, object]]:
        return self._activities


def _as_user(db_session: Session, user_id: int) -> dict[object, object]:
    def _session_override() -> Iterator[Session]:
        yield db_session

    fake_user = UserRecord(
        id=user_id,
        google_subject=f"subject-{user_id}",
        email=f"u{user_id}@x.com",
        created_at=datetime.now(),
    )
    return {
        _get_db_session: _session_override,
        get_current_user: lambda: fake_user,
    }


def test_activities_synced_for_one_user_are_invisible_to_another(
    db_session: Session, user_id: int, other_user_id: int
) -> None:
    with overriding_dependencies(
        {
            **_as_user(db_session, user_id),
            get_garmin_connection: lambda: FakeGarminConnection(
                session=_SyncSource([raw_activity("1")])
            ),
            get_gemini_connection: lambda: FakeGeminiConnection(client=FakeLLMClient("")),
        }
    ):
        sync_response = TestClient(app).post("/sync")
    assert sync_response.status_code == 200
    assert sync_response.json() == {"imported_count": 1}

    with overriding_dependencies(
        {
            **_as_user(db_session, user_id),
            get_garmin_connection: lambda: FakeGarminConnection(session=FakeSource({})),
        }
    ):
        mine = TestClient(app).get("/activities")
    assert [a["garmin_activity_id"] for a in mine.json()] == ["1"]

    with overriding_dependencies(
        {
            **_as_user(db_session, other_user_id),
            get_garmin_connection: lambda: FakeGarminConnection(session=FakeSource({})),
        }
    ):
        client = TestClient(app)
        theirs = client.get("/activities")
        single = client.get("/activities/1")

    assert theirs.json() == []
    assert single.status_code == 404


def test_objectif_and_plan_are_isolated_per_user(
    db_session: Session, user_id: int, other_user_id: int
) -> None:
    with overriding_dependencies(
        {
            **_as_user(db_session, user_id),
            get_garmin_connection: lambda: FakeGarminConnection(session=FakeSource({})),
            get_gemini_connection: lambda: FakeGeminiConnection(
                client=FakeLLMClient('[{"day_offset": 0, "type": "easy", "distance_meters": 5000}]')
            ),
        }
    ):
        create_response = TestClient(app).post(
            "/objectif",
            json={
                "sport": "running",
                "target_distance_meters": 10_000,
                "target_date": "2026-12-01",
            },
        )
    assert create_response.status_code == 200

    with overriding_dependencies({**_as_user(db_session, other_user_id)}):
        client = TestClient(app)
        objectif_response = client.get("/objectif")
        plan_response = client.get("/plan")

    assert objectif_response.status_code == 404
    assert plan_response.status_code == 404


def test_updating_a_seance_is_isolated_per_user(
    db_session: Session, user_id: int, other_user_id: int
) -> None:
    with overriding_dependencies(
        {
            **_as_user(db_session, user_id),
            get_garmin_connection: lambda: FakeGarminConnection(session=FakeSource({})),
            get_gemini_connection: lambda: FakeGeminiConnection(
                client=FakeLLMClient('[{"day_offset": 0, "type": "easy", "distance_meters": 5000}]')
            ),
        }
    ):
        client = TestClient(app)
        client.post(
            "/objectif",
            json={
                "sport": "running",
                "target_distance_meters": 10_000,
                "target_date": "2026-12-01",
            },
        )
        seance_id = client.get("/plan").json()["seances"][0]["id"]

    with overriding_dependencies({**_as_user(db_session, other_user_id)}):
        response = TestClient(app).patch(
            f"/plan/seances/{seance_id}", json={"distance_meters": 999}
        )

    assert response.status_code == 404


def test_rapport_generated_for_one_users_activity_is_invisible_to_another(
    db_session: Session, user_id: int, other_user_id: int
) -> None:
    with overriding_dependencies(
        {
            **_as_user(db_session, user_id),
            get_garmin_connection: lambda: FakeGarminConnection(
                session=_SyncSource([raw_activity("1")])
            ),
            get_gemini_connection: lambda: FakeGeminiConnection(
                client=FakeLLMClient(_rapport_llm_response())
            ),
        }
    ):
        client = TestClient(app)
        client.post("/sync")
        rapport_response = client.post("/activities/1/rapport")
    assert rapport_response.status_code == 200

    with overriding_dependencies(
        {
            **_as_user(db_session, other_user_id),
            get_garmin_connection: lambda: FakeGarminConnection(session=FakeSource({})),
        }
    ):
        theirs = TestClient(app).get("/activities/1/rapport")

    assert theirs.status_code == 404
