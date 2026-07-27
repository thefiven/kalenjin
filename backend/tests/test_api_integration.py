from collections.abc import Iterator
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from kalenjin.api import (
    _get_db_session,
    app,
    get_activity_repository,
    get_current_user,
    get_gemini_connection,
)
from kalenjin.auth.domain import UserRecord
from support.api_client import overriding_dependencies
from support.fakes import FakeGeminiConnection, FakeLLMClient, FakeRepository

pytestmark = pytest.mark.integration


def _week_response() -> str:
    return (
        '[{"day_offset": 0, "type": "easy", "distance_meters": 7000}, '
        '{"day_offset": 3, "type": "easy", "distance_meters": 7000}, '
        '{"day_offset": 6, "type": "long_run", "distance_meters": 6000}]'
    )


def test_create_objectif_shares_one_real_session_across_its_two_repositories(
    db_session: Session, user_id: int
) -> None:
    """Only `_get_db_session` (and `get_current_user`, needed for a real `user_id` to
    satisfy the FK — issue #28) is overridden here — `get_objectif_repository` and
    `get_plan_repository` run as their real, session-backed implementations. This is
    the exact same-request cross-repository write `ObjectifAndPlanRepositories` used
    to force a shared session for: an Objectif is saved, then a Plan referencing its id
    is saved immediately after, in the same not-yet-committed transaction. If FastAPI's
    per-request dependency caching ever stopped sharing one session across sibling
    `Depends(get_objectif_repository)`/`Depends(get_plan_repository)` calls, this would
    fail with a foreign key violation instead of silently passing against fakes.
    """

    def _session_override() -> Iterator[Session]:
        yield db_session

    fake_user = UserRecord(
        id=user_id, google_subject="s", email="user@example.com", created_at=datetime.now()
    )

    with overriding_dependencies(
        {
            _get_db_session: _session_override,
            get_activity_repository: lambda: FakeRepository(),
            get_gemini_connection: lambda: FakeGeminiConnection(
                client=FakeLLMClient(_week_response())
            ),
            get_current_user: lambda: fake_user,
        }
    ):
        response = TestClient(app).post(
            "/objectif",
            json={
                "sport": "running",
                "target_distance_meters": 10_000,
                "target_date": str(date.today() + timedelta(weeks=8)),
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["objectif_id"] is not None
    assert len(body["seances"]) > 0
