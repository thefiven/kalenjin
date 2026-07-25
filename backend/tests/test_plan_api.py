import json
from dataclasses import replace
from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient

from kalenjin.api import (
    app,
    get_activity_repository,
    get_activity_source,
    get_llm_client,
    get_objectif_repository,
    get_plan_repository,
    get_rapport_repository,
)
from kalenjin.plan.domain import ObjectifRecord, PlanRecord, SeanceRecord
from kalenjin.sync.domain import ActivityRecord
from support.api_client import overriding_dependencies
from support.fakes import (
    FakeGarminPushClient,
    FakeLLMClient,
    FakeObjectifRepository,
    FakePlanRepository,
    FakeRapportRepository,
    FakeRepository,
)

MONDAY = date(2026, 1, 5)


def _week_response() -> str:
    return json.dumps(
        [
            {"day_offset": 0, "type": "easy", "distance_meters": 7000},
            {"day_offset": 3, "type": "easy", "distance_meters": 7000},
            {"day_offset": 6, "type": "long_run", "distance_meters": 6000},
        ]
    )


def _objectif(target_date: date = MONDAY + timedelta(weeks=1)) -> ObjectifRecord:
    return ObjectifRecord(
        id=1,
        sport="running",
        target_distance_meters=10_000,
        target_date=target_date,
        target_time_seconds=None,
        created_at=datetime(2026, 1, 1, 8, 0),
    )


def _detailed_seance(
    id: int, scheduled_date: date, status: str = "pending", distance_meters: float = 5000
) -> SeanceRecord:
    return SeanceRecord(
        id=id,
        plan_id=1,
        week_start=MONDAY,
        phase="base",
        detail="detailed",
        scheduled_date=scheduled_date,
        seance_type="easy",
        distance_meters=distance_meters,
        theme=None,
        week_volume_meters=20_000,
        status=status,
        garmin_activity_id=None,
        garmin_workout_id=None,
    )


def _coarse_seance(id: int, week_start: date) -> SeanceRecord:
    return SeanceRecord(
        id=id,
        plan_id=1,
        week_start=week_start,
        phase="base",
        detail="coarse",
        scheduled_date=None,
        seance_type=None,
        distance_meters=None,
        theme="Base — ~20km target volume",
        week_volume_meters=20_000,
        status="pending",
        garmin_activity_id=None,
        garmin_workout_id=None,
    )


def test_create_objectif_generates_and_persists_a_plan() -> None:
    objectif_repo = FakeObjectifRepository()
    plan_repo = FakePlanRepository()
    activity_repo = FakeRepository()
    llm = FakeLLMClient(_week_response())

    with overriding_dependencies(
        {
            get_objectif_repository: lambda: objectif_repo,
            get_plan_repository: lambda: plan_repo,
            get_activity_repository: lambda: activity_repo,
            get_llm_client: lambda: llm,
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
    assert objectif_repo.get_active() is not None
    assert plan_repo.get_active() is not None


def test_get_active_objectif_returns_404_when_none_exists() -> None:
    with overriding_dependencies({get_objectif_repository: lambda: FakeObjectifRepository()}):
        response = TestClient(app).get("/objectif")

    assert response.status_code == 404


def test_get_active_objectif_returns_it_when_present() -> None:
    repo = FakeObjectifRepository(existing=[_objectif()])

    with overriding_dependencies({get_objectif_repository: lambda: repo}):
        response = TestClient(app).get("/objectif")

    assert response.status_code == 200
    assert response.json()["sport"] == "running"


def test_get_active_plan_returns_404_when_none_exists() -> None:
    with overriding_dependencies({get_plan_repository: lambda: FakePlanRepository()}):
        response = TestClient(app).get("/plan")

    assert response.status_code == 404


def test_get_active_plan_returns_its_seances() -> None:
    plan_repo = FakePlanRepository(
        existing=PlanRecord(
            id=1,
            objectif_id=1,
            created_at=datetime(2026, 1, 1, 8, 0),
            seances=[_detailed_seance(1, MONDAY)],
        )
    )

    with overriding_dependencies({get_plan_repository: lambda: plan_repo}):
        response = TestClient(app).get("/plan")

    assert response.status_code == 200
    body = response.json()
    assert len(body["seances"]) == 1
    assert body["seances"][0]["detail"] == "detailed"


def test_patch_seance_updates_it() -> None:
    plan_repo = FakePlanRepository(
        existing=PlanRecord(
            id=1,
            objectif_id=1,
            created_at=datetime(2026, 1, 1, 8, 0),
            seances=[_detailed_seance(1, MONDAY, distance_meters=5000)],
        )
    )

    with overriding_dependencies({get_plan_repository: lambda: plan_repo}):
        response = TestClient(app).patch(
            "/plan/seances/1", json={"distance_meters": 8000, "seance_type": "tempo"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["distance_meters"] == 8000
    assert body["seance_type"] == "tempo"
    assert plan_repo.get_active().seances[0].distance_meters == 8000


def test_patch_seance_returns_404_when_missing() -> None:
    plan_repo = FakePlanRepository(
        existing=PlanRecord(id=1, objectif_id=1, created_at=datetime(2026, 1, 1, 8, 0), seances=[])
    )

    with overriding_dependencies({get_plan_repository: lambda: plan_repo}):
        response = TestClient(app).patch("/plan/seances/999", json={"distance_meters": 1})

    assert response.status_code == 404


def test_generating_a_rapport_with_a_pain_flag_adjusts_the_upcoming_plan() -> None:
    activity_repo = FakeRepository(
        existing=[
            ActivityRecord(
                garmin_activity_id="1",
                sport="running",
                started_at=datetime(2026, 1, 5, 7, 0),
                duration_seconds=1800.0,
                distance_meters=5000.0,
                average_heart_rate=150.0,
                raw_payload={},
            )
        ]
    )
    rapport_repo = FakeRapportRepository()
    objectif_repo = FakeObjectifRepository(existing=[_objectif()])
    plan_repo = FakePlanRepository(
        existing=PlanRecord(
            id=1,
            objectif_id=1,
            created_at=datetime(2026, 1, 1, 8, 0),
            seances=[_detailed_seance(1, date.today() + timedelta(days=2), distance_meters=8000)],
        )
    )
    llm = FakeLLMClient(
        '{"strengths": "x", "improvements": "y", "completed_as_planned": false, '
        '"perceived_effort": "high", "flag": "pain"}'
    )
    garmin = FakeGarminPushClient()

    with overriding_dependencies(
        {
            get_activity_repository: lambda: activity_repo,
            get_rapport_repository: lambda: rapport_repo,
            get_objectif_repository: lambda: objectif_repo,
            get_plan_repository: lambda: plan_repo,
            get_activity_source: lambda: garmin,
            get_llm_client: lambda: llm,
        }
    ):
        response = TestClient(app).post("/activities/1/rapport")

    assert response.status_code == 200
    updated = plan_repo.get_active().seances[0]
    assert updated.seance_type == "easy"
    assert (updated.distance_meters or 0) < 8000
    assert len(garmin.pushed) == 1
    assert updated.garmin_workout_id == "workout-1"


class _EmptySource:
    def fetch_activities(self, start_date: date, end_date: date) -> list[dict]:  # type: ignore[type-arg]
        return []


def test_sync_marks_past_due_seances_completed_against_synced_activities() -> None:
    past_scheduled = date.today() - timedelta(days=1)
    activity_repo = FakeRepository(
        existing=[
            ActivityRecord(
                garmin_activity_id="a1",
                sport="running",
                started_at=datetime.combine(past_scheduled, datetime.min.time()),
                duration_seconds=1800.0,
                distance_meters=5000.0,
                average_heart_rate=150.0,
                raw_payload={},
            )
        ]
    )
    objectif_repo = FakeObjectifRepository(existing=[_objectif()])
    plan_repo = FakePlanRepository(
        existing=PlanRecord(
            id=1,
            objectif_id=1,
            created_at=datetime(2026, 1, 1, 8, 0),
            seances=[_detailed_seance(1, past_scheduled)],
        )
    )

    with overriding_dependencies(
        {
            get_activity_source: lambda: _EmptySource(),
            get_activity_repository: lambda: activity_repo,
            get_objectif_repository: lambda: objectif_repo,
            get_plan_repository: lambda: plan_repo,
            get_llm_client: lambda: FakeLLMClient(_week_response()),
        }
    ):
        response = TestClient(app).post("/sync")

    assert response.status_code == 200
    updated = plan_repo.get_active().seances[0]
    assert updated.status == "completed"
    assert updated.garmin_activity_id == "a1"


def test_sync_pushes_a_never_pushed_upcoming_seance() -> None:
    objectif_repo = FakeObjectifRepository(existing=[_objectif()])
    plan_repo = FakePlanRepository(
        existing=PlanRecord(
            id=1,
            objectif_id=1,
            created_at=datetime(2026, 1, 1, 8, 0),
            seances=[_detailed_seance(1, date.today() + timedelta(days=2))],
        )
    )
    garmin = FakeGarminPushClient()

    with overriding_dependencies(
        {
            get_activity_source: lambda: garmin,
            get_activity_repository: lambda: FakeRepository(),
            get_objectif_repository: lambda: objectif_repo,
            get_plan_repository: lambda: plan_repo,
            get_llm_client: lambda: FakeLLMClient(_week_response()),
        }
    ):
        response = TestClient(app).post("/sync")

    assert response.status_code == 200
    assert len(garmin.pushed) == 1
    assert plan_repo.get_active().seances[0].garmin_workout_id == "workout-1"


def test_sync_does_not_re_push_an_already_pushed_unchanged_seance() -> None:
    objectif_repo = FakeObjectifRepository(existing=[_objectif()])
    plan_repo = FakePlanRepository(
        existing=PlanRecord(
            id=1,
            objectif_id=1,
            created_at=datetime(2026, 1, 1, 8, 0),
            seances=[
                _detailed_seance(1, date.today() + timedelta(days=2)),
            ],
        )
    )
    # Simulate an earlier successful push by giving the seance a workout id already.
    plan_repo.update_seances(
        [replace(plan_repo.get_active().seances[0], garmin_workout_id="already-pushed")]
    )
    garmin = FakeGarminPushClient()

    with overriding_dependencies(
        {
            get_activity_source: lambda: garmin,
            get_activity_repository: lambda: FakeRepository(),
            get_objectif_repository: lambda: objectif_repo,
            get_plan_repository: lambda: plan_repo,
            get_llm_client: lambda: FakeLLMClient(_week_response()),
        }
    ):
        response = TestClient(app).post("/sync")

    assert response.status_code == 200
    assert garmin.pushed == []
    assert garmin.deleted == []
    assert plan_repo.get_active().seances[0].garmin_workout_id == "already-pushed"
